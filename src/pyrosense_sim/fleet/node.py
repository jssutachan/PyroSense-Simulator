"""A simulated sensor node: noisy instrument over the ground-truth environment.

Each node owns its seeded RNG (derived from the scenario seed and its
``device_id``, so fleets are deterministic regardless of scheduling
order), a strictly monotonic ``seq`` counter, a slowly draining battery
and an adaptive sampling cadence: ``t_normal_s`` normally, dropping to
``t_alert_s`` while its own readings cross the local alert thresholds.
"""

import random
from datetime import datetime, timedelta

from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload
from pyrosense_sim.fleet.config import NodeConfig
from pyrosense_sim.fleet.environment import EnvironmentModel
from pyrosense_sim.planner.zones import Tier


class SensorNode:
    """Mutable per-device simulation state and sampling behavior."""

    def __init__(
        self,
        *,
        device_id: str,
        gateway_id: str,
        lon: float,
        lat: float,
        elevation_m: float,
        tier: Tier,
        has_wind_sensor: bool,
        config: NodeConfig,
        start_time: datetime,
        seed: int,
    ) -> None:
        """Create a node at its planned site.

        Args:
            device_id: Contract-format id (``PYRO-T{tier}-{seq:04d}``).
            gateway_id: Gateway this node reports through (metadata).
            lon: Longitude in decimal degrees.
            lat: Latitude in decimal degrees.
            elevation_m: Site elevation from the plan.
            tier: Priority tier (1|2|3).
            has_wind_sensor: Whether wind fields carry values or ``null``.
            config: Behavior parameters (cadence, battery, noise).
            start_time: Scenario start; ``ts_device`` = start + sim time.
            seed: Base scenario seed; the node derives its own RNG from
                ``{seed}:{device_id}`` so per-node streams are independent
                and reproducible.
        """
        self.device_id = device_id
        self.gateway_id = gateway_id
        self.lon = lon
        self.lat = lat
        self.elevation_m = elevation_m
        self.tier = tier
        self.has_wind_sensor = has_wind_sensor
        self._config = config
        self._start_time = start_time
        self._rng = random.Random(f"{seed}:{device_id}")
        self._seq = 0
        self._battery_pct = config.battery_start_pct
        self._last_sample_t: float | None = None
        self._interval_s = config.t_normal_s

    @property
    def interval_s(self) -> float:
        """Seconds until the next sample: ``t_alert_s`` while readings are elevated."""
        return self._interval_s

    @property
    def battery_pct(self) -> float:
        """Current battery level (drains with simulated time)."""
        return self._battery_pct

    def sample(self, environment: EnvironmentModel, t_s: float) -> TelemetryPayload:
        """Measure the environment and emit a validated v1 payload.

        Consults ground truth, applies this node's gaussian sensor noise,
        drains the battery by the elapsed simulated time, increments
        ``seq`` and adapts the sampling cadence.

        Args:
            environment: Ground-truth conditions oracle.
            t_s: Simulated seconds since scenario start.

        Returns:
            A contract-valid payload (validation runs on every emission).
        """
        conditions = environment.conditions_at(self.lon, self.lat, self.elevation_m, t_s)
        cfg = self._config
        gauss = self._rng.gauss

        temp = conditions.temp_c + gauss(0.0, cfg.sigma_temp_c)
        rh = min(100.0, max(0.0, conditions.rh_pct + gauss(0.0, cfg.sigma_rh_pct)))
        smoke = max(0.0, conditions.smoke_ppm + gauss(0.0, cfg.sigma_smoke_ppm))
        wind_speed: float | None = None
        wind_dir: float | None = None
        if self.has_wind_sensor:
            wind_speed = max(0.0, conditions.wind_speed_ms + gauss(0.0, cfg.sigma_wind_ms))
            wind_dir = (conditions.wind_dir_deg + gauss(0.0, cfg.sigma_wind_dir_deg)) % 360.0

        self._drain_battery(t_s)
        self._seq += 1
        self._interval_s = (
            cfg.t_alert_s
            if temp > cfg.alert_temp_c or smoke > cfg.alert_smoke_ppm
            else cfg.t_normal_s
        )
        return TelemetryPayload(
            device_id=self.device_id,
            gateway_id=self.gateway_id,
            ts_device=self._start_time + timedelta(seconds=t_s),
            seq=self._seq - 1,
            lat=self.lat,
            lon=self.lon,
            elevation_m=self.elevation_m,
            temp_c=temp,
            rh_pct=rh,
            smoke_ppm=smoke,
            wind_speed_ms=wind_speed,
            wind_dir_deg=wind_dir,
            battery_pct=self._battery_pct,
            status=self._status(),
        )

    def _drain_battery(self, t_s: float) -> None:
        elapsed = 0.0 if self._last_sample_t is None else t_s - self._last_sample_t
        self._last_sample_t = t_s
        drain = self._config.battery_drain_pct_per_day * (elapsed / 86_400.0)
        self._battery_pct = max(0.0, self._battery_pct - drain)

    def _status(self) -> DeviceStatus:
        if self._battery_pct < self._config.degraded_battery_pct:
            return DeviceStatus.DEGRADED
        if self._battery_pct < self._config.low_battery_pct:
            return DeviceStatus.LOW_BATTERY
        return DeviceStatus.OK
