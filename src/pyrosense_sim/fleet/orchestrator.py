"""Fleet orchestrator: composes plan + environment + scheduler + publisher.

The orchestrator is pure wiring (DIP): it loads the site plan produced
by the site-planner, instantiates one :class:`SensorNode` per feature,
and drives the scheduler loop pushing every payload into an injected
:class:`~pyrosense_sim.publishers.base.Publisher`. It never knows which
transport is behind the interface.

``run()`` is cleanly cancelable: a SIGINT (KeyboardInterrupt) stops the
loop, the publisher is flushed/closed, and the summary is logged and
returned either way.
"""

import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pyrosense_sim.fleet.config import ScenarioConfig
from pyrosense_sim.fleet.environment import EnvironmentModel
from pyrosense_sim.fleet.faults import FaultInjector
from pyrosense_sim.fleet.fire_event import FireEvent
from pyrosense_sim.fleet.node import SensorNode
from pyrosense_sim.fleet.scheduler import Scheduler
from pyrosense_sim.planner.zones import Tier
from pyrosense_sim.publishers.base import Publisher

logger = logging.getLogger(__name__)

_REQUIRED_PROPERTIES = ("device_id", "gateway_id", "tier", "elevation_m", "has_wind_sensor")


@dataclass(frozen=True)
class FleetSummary:
    """Final accounting of a fleet run."""

    emitted: int
    by_status: dict[str, int]
    simulated_s: float
    real_s: float
    interrupted: bool


class FleetOrchestrator:
    """Drives a full fleet simulation run."""

    def __init__(
        self,
        nodes: list[SensorNode],
        environment: EnvironmentModel,
        scheduler: Scheduler,
        publisher: Publisher,
    ) -> None:
        """Wire the composed parts (see :meth:`from_files` for the usual path)."""
        self._nodes = nodes
        self._environment = environment
        self._scheduler = scheduler
        self._publisher = publisher

    @classmethod
    def from_files(
        cls,
        site_path: Path,
        scenario: ScenarioConfig,
        publisher: Publisher,
        *,
        speed: float = 60.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> "FleetOrchestrator":
        """Build an orchestrator from a site plan file and a scenario.

        Args:
            site_path: ``sensores.geojson`` produced by the site-planner.
            scenario: Validated scenario configuration.
            publisher: Destination for every payload (stdout, file, ...).
            speed: Simulated-to-real time factor for the scheduler.
            sleep_fn: Pacing function override (tests use a no-op).

        Returns:
            A ready-to-run orchestrator.

        Raises:
            ValueError: If the site plan is empty or a feature misses
                required properties.
        """
        nodes = _load_nodes(site_path, scenario)
        fires = tuple(FireEvent.from_config(fire) for fire in scenario.fires)
        environment = EnvironmentModel(scenario.environment, fires)
        scheduler = Scheduler(nodes, duration_s=scenario.duration_s, speed=speed, sleep_fn=sleep_fn)
        if scenario.faults is not None:
            publisher = FaultInjector(
                publisher, scenario.faults, start_time=scenario.start_time, seed=scenario.seed
            )
        return cls(nodes, environment, scheduler, publisher)

    def run(self) -> FleetSummary:
        """Run the simulation to the horizon (or until SIGINT), then close.

        Returns:
            The run summary; it is also logged at INFO level.
        """
        started = time.perf_counter()
        emitted = 0
        by_status: Counter[str] = Counter()
        last_t = 0.0
        interrupted = False
        logger.info("fleet run starting: %d nodes", len(self._nodes))
        try:
            for t_s, node in self._scheduler.run():
                payload = node.sample(self._environment, t_s)
                self._publisher.publish(payload)
                emitted += 1
                by_status[payload.status.value] += 1
                last_t = t_s
        except KeyboardInterrupt:
            interrupted = True
            logger.info("SIGINT received; flushing publisher and closing")
        finally:
            self._publisher.close()

        summary = FleetSummary(
            emitted=emitted,
            by_status=dict(by_status),
            simulated_s=last_t,
            real_s=time.perf_counter() - started,
            interrupted=interrupted,
        )
        logger.info(
            "fleet run %s: %d payloads (%s), %.0f s simulated in %.2f s real",
            "interrupted" if interrupted else "finished",
            summary.emitted,
            ", ".join(f"{status}={count}" for status, count in sorted(summary.by_status.items()))
            or "none",
            summary.simulated_s,
            summary.real_s,
        )
        return summary


def _load_nodes(site_path: Path, scenario: ScenarioConfig) -> list[SensorNode]:
    """Instantiate the fleet from a sensores.geojson FeatureCollection.

    When the scenario sets ``load.fleet_multiplier > 1`` the fleet is
    replicated with derived, contract-valid device ids (see
    :func:`_replicate_specs`) to stress the pipeline without a bigger plan.
    """
    collection = json.loads(Path(site_path).read_text(encoding="utf-8"))
    features = collection.get("features") or []
    if not features:
        msg = f"site plan {site_path} has no features; generate it with site-planner"
        raise ValueError(msg)
    specs: list[dict[str, object]] = []
    for feature in features:
        properties = feature.get("properties") or {}
        missing = [key for key in _REQUIRED_PROPERTIES if key not in properties]
        if missing:
            msg = f"feature {properties.get('device_id', '?')} misses properties {missing}"
            raise ValueError(msg)
        lon, lat = feature["geometry"]["coordinates"]
        tier = properties["tier"]
        if tier not in (1, 2, 3):
            msg = f"feature {properties['device_id']} has invalid tier {tier!r}"
            raise ValueError(msg)
        specs.append(
            {
                "device_id": properties["device_id"],
                "gateway_id": properties["gateway_id"],
                "lon": float(lon),
                "lat": float(lat),
                "elevation_m": float(properties["elevation_m"]),
                "tier": tier,
                "has_wind_sensor": bool(properties["has_wind_sensor"]),
            }
        )
    specs = _replicate_specs(specs, scenario.load.fleet_multiplier)
    return [
        SensorNode(
            device_id=cast(str, spec["device_id"]),
            gateway_id=cast(str, spec["gateway_id"]),
            lon=cast(float, spec["lon"]),
            lat=cast(float, spec["lat"]),
            elevation_m=cast(float, spec["elevation_m"]),
            tier=cast(Tier, spec["tier"]),
            has_wind_sensor=cast(bool, spec["has_wind_sensor"]),
            config=scenario.node,
            start_time=scenario.start_time,
            seed=scenario.seed,
        )
        for spec in specs
    ]


def _replicate_specs(specs: list[dict[str, object]], multiplier: int) -> list[dict[str, object]]:
    """Replicate the fleet for load testing with derived device ids.

    Replica ``r`` of the node at per-tier position ``p`` gets serial
    ``max_original_serial_of_tier * r + p``, which stays inside the
    contract pattern ``PYRO-T{tier}-\\d{4}`` and never collides with the
    originals. Positions and RNG streams derive from the new device_id,
    so replicas emit independent (but reproducible) telemetry.

    Raises:
        ValueError: If a derived serial would exceed 9999 (the contract
            id format is full for that tier).
    """
    if multiplier == 1:
        return specs
    max_serial: dict[object, int] = {}
    position: list[int] = []
    seen: dict[object, int] = {}
    for spec in specs:
        tier = spec["tier"]
        serial = int(cast(str, spec["device_id"])[-4:])
        max_serial[tier] = max(max_serial.get(tier, 0), serial)
        seen[tier] = seen.get(tier, 0) + 1
        position.append(seen[tier])

    replicated = list(specs)
    for replica in range(1, multiplier):
        for spec, tier_position in zip(specs, position, strict=True):
            tier = spec["tier"]
            serial = max_serial[tier] * replica + tier_position
            if serial > 9999:
                msg = (
                    f"fleet_multiplier={multiplier} overflows the 4-digit device_id "
                    f"serial for tier {tier} (needs {serial})"
                )
                raise ValueError(msg)
            replicated.append({**spec, "device_id": f"PYRO-T{tier}-{serial:04d}"})
    return replicated
