"""Parametric fire events: plausible multi-sensor signals, NOT fire physics.

A :class:`FireEvent` is pure interpolation (ADR-0011): a circle whose
radius grows linearly, whose center drifts with a configurable wind
vector, and whose signal deltas (temp up, humidity down, smoke way up)
scale with an intensity in [0, 1]. Intensity ramps in smoothly after
ignition (smoothstep) and decays linearly with distance beyond the
front across a ``halo``. That is everything: no fuel models, no rate
of spread, no Rothermel — the goal is to exercise the detection
pipeline with spatially correlated readings, not to predict fires.
"""

from dataclasses import dataclass

from pyrosense_sim.fleet.config import FireEventConfig
from pyrosense_sim.fleet.environment import Conditions
from pyrosense_sim.planner.geo import distance_m, meters_to_deg_lat, meters_to_deg_lon


@dataclass(frozen=True)
class FireEvent:
    """One parametric fire (internal value object; built from config)."""

    epicenter_lon: float
    epicenter_lat: float
    start_s: float
    initial_radius_m: float
    growth_m_per_min: float
    wind_east_m_per_min: float
    wind_north_m_per_min: float
    ramp_s: float
    halo_m: float
    peak_temp_delta_c: float
    peak_rh_drop_pct: float
    peak_smoke_ppm: float

    @classmethod
    def from_config(cls, config: FireEventConfig) -> "FireEvent":
        """Convert the validated scenario block into the internal value object."""
        return cls(
            epicenter_lon=config.epicenter_lon,
            epicenter_lat=config.epicenter_lat,
            start_s=config.start_hour * 3600.0,
            initial_radius_m=config.initial_radius_m,
            growth_m_per_min=config.growth_rate_m_per_min,
            wind_east_m_per_min=config.wind_bias.east_m_per_min,
            wind_north_m_per_min=config.wind_bias.north_m_per_min,
            ramp_s=config.ramp_minutes * 60.0,
            halo_m=config.halo_m,
            peak_temp_delta_c=config.peak_temp_delta_c,
            peak_rh_drop_pct=config.peak_rh_drop_pct,
            peak_smoke_ppm=config.peak_smoke_ppm,
        )

    def intensity_at(self, lon: float, lat: float, t_s: float) -> float:
        """Fire intensity in [0, 1] at a point and simulated time.

        Zero before ignition and beyond the halo; 1.0 inside the burning
        front once the temporal ramp completes.
        """
        if t_s < self.start_s:
            return 0.0
        minutes = (t_s - self.start_s) / 60.0
        center_lon = self.epicenter_lon + meters_to_deg_lon(
            self.wind_east_m_per_min * minutes, self.epicenter_lat
        )
        center_lat = self.epicenter_lat + meters_to_deg_lat(self.wind_north_m_per_min * minutes)
        radius = self.initial_radius_m + self.growth_m_per_min * minutes

        distance = distance_m(lon, lat, center_lon, center_lat)
        if distance <= radius:
            falloff = 1.0
        elif self.halo_m > 0.0 and distance < radius + self.halo_m:
            falloff = 1.0 - (distance - radius) / self.halo_m
        else:
            return 0.0

        progress = min(1.0, (t_s - self.start_s) / self.ramp_s)
        ramp = progress * progress * (3.0 - 2.0 * progress)  # smoothstep
        return ramp * falloff

    def perturb(self, conditions: Conditions, lon: float, lat: float, t_s: float) -> Conditions:
        """Apply the fire's signal deltas to baseline conditions.

        Args:
            conditions: Baseline (or already-perturbed) ground truth.
            lon: Longitude of the queried point.
            lat: Latitude of the queried point.
            t_s: Simulated seconds since scenario start.

        Returns:
            New conditions with temp up, humidity down (clamped at 0) and
            smoke up, scaled by intensity. Wind is left untouched.
        """
        intensity = self.intensity_at(lon, lat, t_s)
        if intensity <= 0.0:
            return conditions
        return Conditions(
            temp_c=conditions.temp_c + self.peak_temp_delta_c * intensity,
            rh_pct=max(0.0, conditions.rh_pct - self.peak_rh_drop_pct * intensity),
            smoke_ppm=conditions.smoke_ppm + self.peak_smoke_ppm * intensity,
            wind_speed_ms=conditions.wind_speed_ms,
            wind_dir_deg=conditions.wind_dir_deg,
        )
