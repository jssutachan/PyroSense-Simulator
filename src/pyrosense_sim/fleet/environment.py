"""Baseline environment model: ground-truth conditions at any point and time.

Design decision (ADR-0009): the environment is a **pure, deterministic
function** of (position, elevation, time) — it represents physical
ground truth. Measurement noise belongs to the sensors
(:class:`~pyrosense_sim.fleet.node.SensorNode` adds seeded gaussian
noise per node), because in the real system it is the instrument that
is noisy, not the atmosphere. This also makes determinism trivial to
reason about: the only RNGs in the simulation live in the nodes.

Baseline physics (reasoned approximations):

- Diurnal temperature: sinusoid with configurable mean, amplitude and
  peak hour.
- Elevation modulation: linear lapse rate (default -6.5 C/km, the
  standard atmosphere value) relative to a reference elevation.
- Relative humidity: anticorrelated sinusoid (driest at the warmest
  hour), clamped to [0, 100].
- Wind and smoke: constant baseline means.

Path 6 hook: fire events will perturb the baseline in
:meth:`EnvironmentModel.conditions_at`; in this path the event list is
empty by construction.
"""

from dataclasses import dataclass
from math import cos, pi

from pyrosense_sim.fleet.config import EnvironmentConfig


@dataclass(frozen=True)
class Conditions:
    """Ground-truth environmental conditions at one point and instant."""

    temp_c: float
    rh_pct: float
    smoke_ppm: float
    wind_speed_ms: float
    wind_dir_deg: float


class EnvironmentModel:
    """Deterministic baseline conditions over the AOI."""

    def __init__(self, config: EnvironmentConfig) -> None:
        """Configure the model.

        Args:
            config: Validated environment parameters from the scenario.
        """
        self._config = config

    def conditions_at(self, lon: float, lat: float, elevation_m: float, t_s: float) -> Conditions:
        """Ground-truth conditions at a position and simulated time.

        Args:
            lon: Longitude in decimal degrees (unused by the baseline
                model; kept for the Path 6 fire-event hook, which is
                spatial).
            lat: Latitude in decimal degrees (same as ``lon``).
            elevation_m: Site elevation in meters.
            t_s: Simulated seconds since scenario start.

        Returns:
            The noise-free conditions a perfect instrument would read.
        """
        del lon, lat  # baseline is spatially uniform; fire events (P6) will not be
        cfg = self._config
        hour = (t_s / 3600.0) % 24.0
        diurnal = cos(2.0 * pi * (hour - cfg.temp_peak_hour) / 24.0)

        temp = (
            cfg.temp_mean_c
            + cfg.temp_amplitude_c * diurnal
            + cfg.lapse_rate_c_per_km * (elevation_m - cfg.reference_elevation_m) / 1000.0
        )
        rh = _clamp(cfg.rh_mean_pct - cfg.rh_amplitude_pct * diurnal, 0.0, 100.0)
        # Path 6 hook: fire events will perturb temp/smoke/rh here.
        return Conditions(
            temp_c=temp,
            rh_pct=rh,
            smoke_ppm=cfg.smoke_baseline_ppm,
            wind_speed_ms=cfg.wind_speed_mean_ms,
            wind_dir_deg=cfg.wind_dir_mean_deg,
        )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
