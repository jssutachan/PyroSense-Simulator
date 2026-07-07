"""Composable fault injection over the message stream.

The :class:`FaultInjector` is a **decorator over the Publisher
protocol** (ADR-0012): it satisfies ``Publisher`` itself and wraps any
other publisher, so faults are injected at the transport seam without
touching :class:`~pyrosense_sim.fleet.node.SensorNode` — nodes keep
behaving like healthy hardware; the *network and the field* are what
misbehave. Injectors can stack on each other or on any transport.

Faults (each independently optional, driven by
:class:`~pyrosense_sim.fleet.config.FaultsConfig`):

- ``node_dropout`` — a per-device deterministic draw silences a
  fraction of nodes during periodic windows.
- ``burst_reconnect`` — a device or a whole gateway buffers everything
  during its offline window and replays the backlog in one burst on
  reconnection, with the ORIGINAL (old) ``ts_device`` and consecutive
  ``seq`` — exactly the pattern the cloud must not confuse with a
  real alert.
- ``duplicates`` — random re-delivery with identical ``device_id`` +
  ``seq`` (MQTT QoS 1 at-least-once).
- ``out_of_order`` — local permutation within a sliding window.
- ``battery_decay`` — rewrites ``battery_pct``/``status`` on the
  stream to accelerate degradation.

Simulated time is read from each payload's ``ts_device``: the injector
never needs a clock of its own, which keeps it deterministic and
transport-agnostic.
"""

import logging
import random
from collections import Counter
from datetime import datetime

from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload
from pyrosense_sim.fleet.config import FaultsConfig
from pyrosense_sim.publishers.base import Publisher

logger = logging.getLogger(__name__)


class FaultInjector:
    """Publisher decorator that perturbs the message stream."""

    def __init__(
        self,
        inner: Publisher,
        config: FaultsConfig,
        *,
        start_time: datetime,
        seed: int = 0,
    ) -> None:
        """Wrap ``inner`` with the configured faults.

        Args:
            inner: The next stage (a transport or another injector).
            config: Which faults to apply and how.
            start_time: Scenario start; elapsed simulated time is derived
                from each payload's ``ts_device`` against it.
            seed: Seed for the stream-level RNG (duplicates, shuffling)
                and the per-device dropout draws.
        """
        self._inner = inner
        self._config = config
        self._start_time = start_time
        self._seed = seed
        self._rng = random.Random(f"{seed}:faults")
        self._dropout_members: dict[str, bool] = {}
        self._backlog: list[TelemetryPayload] = []
        self._reorder_buffer: list[TelemetryPayload] = []
        self._stats: Counter[str] = Counter()

    def publish(self, payload: TelemetryPayload) -> None:
        """Run the payload through the fault chain (some never come out).

        Args:
            payload: A contract-valid payload from the fleet.
        """
        payload = self._apply_battery_decay(payload)
        if self._dropped(payload):
            self._stats["dropped"] += 1
            return
        if self._buffered_offline(payload):
            self._stats["buffered"] += 1
            return
        self._flush_backlog_if_reconnected(payload)
        self._emit(payload)

    def close(self) -> None:
        """Flush the reorder window, report stats and close the next stage.

        A backlog whose offline window never ended is NOT flushed: the
        device is still offline when the simulation stops, so those
        messages are lost — and counted.
        """
        for held in self._reorder_buffer:
            self._inner.publish(held)
        self._reorder_buffer.clear()
        self._stats["backlog_lost"] = len(self._backlog)
        logger.info(
            "fault injector stats: %s",
            ", ".join(f"{name}={count}" for name, count in sorted(self._stats.items())) or "none",
        )
        self._inner.close()

    # ─── individual faults ───────────────────────────────────────────

    def _apply_battery_decay(self, payload: TelemetryPayload) -> TelemetryPayload:
        cfg = self._config.battery_decay
        if cfg is None:
            return payload
        elapsed_days = self._elapsed_s(payload) / 86_400.0
        battery = max(0.0, payload.battery_pct - cfg.extra_pct_per_day * elapsed_days)
        if battery < cfg.degraded_pct:
            status = DeviceStatus.DEGRADED
        elif battery < cfg.low_pct:
            status = DeviceStatus.LOW_BATTERY
        else:
            status = payload.status
        self._stats["battery_rewritten"] += 1
        return payload.model_copy(update={"battery_pct": battery, "status": status})

    def _dropped(self, payload: TelemetryPayload) -> bool:
        cfg = self._config.node_dropout
        if cfg is None:
            return False
        if payload.device_id not in self._dropout_members:
            # Per-device deterministic draw, independent of arrival order.
            draw = random.Random(f"{self._seed}:dropout:{payload.device_id}").random()
            self._dropout_members[payload.device_id] = draw < cfg.fraction
        if not self._dropout_members[payload.device_id]:
            return False
        position_s = self._elapsed_s(payload) % (cfg.period_min * 60.0)
        return position_s < cfg.window_min * 60.0

    def _offline_window(self) -> tuple[float, float] | None:
        cfg = self._config.burst_reconnect
        if cfg is None:
            return None
        start = cfg.offline_from_hour * 3600.0
        return start, start + cfg.offline_hours * 3600.0

    def _matches_reconnect_target(self, payload: TelemetryPayload) -> bool:
        cfg = self._config.burst_reconnect
        if cfg is None:
            return False
        if cfg.device_id is not None:
            return payload.device_id == cfg.device_id
        return payload.gateway_id == cfg.gateway_id

    def _buffered_offline(self, payload: TelemetryPayload) -> bool:
        window = self._offline_window()
        if window is None or not self._matches_reconnect_target(payload):
            return False
        start_s, end_s = window
        if start_s <= self._elapsed_s(payload) < end_s:
            self._backlog.append(payload)
            return True
        return False

    def _flush_backlog_if_reconnected(self, payload: TelemetryPayload) -> None:
        window = self._offline_window()
        if window is None or not self._backlog:
            return
        if self._elapsed_s(payload) >= window[1]:
            # Reconnection: replay everything at once, original ts_device
            # (old timestamps) and consecutive seq preserved by order.
            self._stats["backlog_flushed"] += len(self._backlog)
            for held in self._backlog:
                self._emit(held)
            self._backlog.clear()

    def _emit(self, payload: TelemetryPayload) -> None:
        """Apply duplicates + reordering, then hand over to the next stage."""
        duplicates = self._config.duplicates
        copies = 1
        if duplicates is not None and self._rng.random() < duplicates.probability:
            copies = 2
            self._stats["duplicated"] += 1
        reorder = self._config.out_of_order
        for _ in range(copies):
            if reorder is None:
                self._inner.publish(payload)
                continue
            self._reorder_buffer.append(payload)
            if len(self._reorder_buffer) >= reorder.window:
                self._rng.shuffle(self._reorder_buffer)
                self._stats["reordered_windows"] += 1
                for held in self._reorder_buffer:
                    self._inner.publish(held)
                self._reorder_buffer.clear()

    def _elapsed_s(self, payload: TelemetryPayload) -> float:
        return (payload.ts_device - self._start_time).total_seconds()
