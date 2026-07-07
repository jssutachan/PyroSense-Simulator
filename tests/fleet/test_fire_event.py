"""Tests for FireEvent: parametric interpolation and multi-sensor correlation."""

import io
import json
from collections import defaultdict
from pathlib import Path

import pytest

from pyrosense_sim.fleet.config import (
    EnvironmentConfig,
    FireEventConfig,
    NodeConfig,
    ScenarioConfig,
    WindBiasConfig,
)
from pyrosense_sim.fleet.environment import EnvironmentModel
from pyrosense_sim.fleet.fire_event import FireEvent
from pyrosense_sim.fleet.orchestrator import FleetOrchestrator
from pyrosense_sim.planner.geo import meters_to_deg_lon
from pyrosense_sim.publishers.stdout import StdoutPublisher

EPICENTER = (-74.05, 4.55)


def make_fire(**overrides: object) -> FireEvent:
    base: dict[str, object] = {
        "epicenter_lon": EPICENTER[0],
        "epicenter_lat": EPICENTER[1],
        "start_hour": 1.0,
        "initial_radius_m": 100.0,
        "growth_rate_m_per_min": 0.0,
        "ramp_minutes": 30.0,
        "halo_m": 200.0,
    }
    base.update(overrides)
    return FireEvent.from_config(FireEventConfig(**base))


def hours(value: float) -> float:
    return value * 3600.0


class TestIntensity:
    def test_zero_before_ignition(self) -> None:
        fire = make_fire(start_hour=1.0)
        assert fire.intensity_at(*EPICENTER, hours(0.5)) == 0.0

    def test_full_inside_front_after_ramp(self) -> None:
        fire = make_fire()
        assert fire.intensity_at(*EPICENTER, hours(2.0)) == 1.0

    def test_ramps_in_smoothly(self) -> None:
        fire = make_fire(ramp_minutes=30.0)
        early = fire.intensity_at(*EPICENTER, hours(1.0) + 300.0)  # 5 min in
        later = fire.intensity_at(*EPICENTER, hours(1.0) + 900.0)  # 15 min in
        assert 0.0 < early < later < 1.0

    def test_decays_across_the_halo_and_dies_beyond(self) -> None:
        fire = make_fire(initial_radius_m=100.0, halo_m=200.0)
        lon_mid_halo = EPICENTER[0] + meters_to_deg_lon(200.0, EPICENTER[1])  # front + 100
        lon_beyond = EPICENTER[0] + meters_to_deg_lon(400.0, EPICENTER[1])  # front + 300
        t_late = hours(3.0)
        assert fire.intensity_at(lon_mid_halo, EPICENTER[1], t_late) == pytest.approx(0.5, abs=0.02)
        assert fire.intensity_at(lon_beyond, EPICENTER[1], t_late) == 0.0

    def test_front_grows_over_time(self) -> None:
        fire = make_fire(growth_rate_m_per_min=2.0, halo_m=0.0)
        lon_400m_out = EPICENTER[0] + meters_to_deg_lon(400.0, EPICENTER[1])
        just_after = fire.intensity_at(lon_400m_out, EPICENTER[1], hours(1.0) + 60.0)
        much_later = fire.intensity_at(lon_400m_out, EPICENTER[1], hours(1.0) + hours(3.0))
        assert just_after == 0.0
        assert much_later == 1.0

    def test_wind_bias_drifts_the_center(self) -> None:
        fire = make_fire(wind_bias=WindBiasConfig(east_m_per_min=-3.0), halo_m=0.0)
        lon_west = EPICENTER[0] + meters_to_deg_lon(-500.0, EPICENTER[1])
        before_drift = fire.intensity_at(lon_west, EPICENTER[1], hours(1.0) + 60.0)
        after_drift = fire.intensity_at(lon_west, EPICENTER[1], hours(1.0) + hours(3.0))
        assert before_drift == 0.0
        assert after_drift == 1.0  # the center walked ~540 m west in 3 h


class TestEnvironmentIntegration:
    def test_near_point_sees_the_signature_far_point_does_not(self) -> None:
        config = EnvironmentConfig()
        clean = EnvironmentModel(config)
        burning = EnvironmentModel(config, fires=(make_fire(),))
        t_late = hours(3.0)

        near_clean = clean.conditions_at(*EPICENTER, 2800.0, t_late)
        near_burning = burning.conditions_at(*EPICENTER, 2800.0, t_late)
        assert near_burning.temp_c > near_clean.temp_c
        assert near_burning.rh_pct < near_clean.rh_pct
        assert near_burning.smoke_ppm > near_clean.smoke_ppm * 100

        far = (-74.02, 4.58)  # ~4.5 km away
        assert burning.conditions_at(*far, 2800.0, t_late) == clean.conditions_at(
            *far, 2800.0, t_late
        )

    def test_rh_never_goes_negative(self) -> None:
        dry = EnvironmentConfig(rh_mean_pct=10.0, rh_amplitude_pct=5.0)
        burning = EnvironmentModel(dry, fires=(make_fire(peak_rh_drop_pct=90.0),))
        conditions = burning.conditions_at(*EPICENTER, 2800.0, hours(14.0))
        assert conditions.rh_pct == 0.0


class TestMultiSensorCorrelation:
    def test_nearby_nodes_correlate_and_distant_ones_do_not(self, tmp_path: Path) -> None:
        site = tmp_path / "sensores.geojson"
        features = []
        # Two nodes inside the fire, one 3 km east (well beyond the halo).
        positions = [EPICENTER, (EPICENTER[0] + 0.0005, EPICENTER[1]), (-74.02, 4.55)]
        for index, (lon, lat) in enumerate(positions):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "device_id": f"PYRO-T1-{index + 1:04d}",
                        "tier": 1,
                        "zone_name": "el_cable",
                        "elevation_m": 2700.0,
                        "slope_deg": 10.0,
                        "gateway_id": "GW-01",
                        "has_wind_sensor": False,
                    },
                }
            )
        site.write_text(json.dumps({"type": "FeatureCollection", "features": features}))

        noiseless = NodeConfig(
            sigma_temp_c=0.0, sigma_rh_pct=0.0, sigma_smoke_ppm=0.0, alert_smoke_ppm=5.0
        )
        scenario = ScenarioConfig(
            name="fire-test",
            duration_hours=3.0,
            seed=1,
            node=noiseless,
            fires=[
                FireEventConfig(
                    **{
                        "epicenter_lon": EPICENTER[0],
                        "epicenter_lat": EPICENTER[1],
                        "start_hour": 1.0,
                        "initial_radius_m": 150.0,
                        "ramp_minutes": 20.0,
                    }
                )
            ],
        )
        stream = io.StringIO()
        FleetOrchestrator.from_files(
            site, scenario, StdoutPublisher(stream=stream), sleep_fn=lambda _: None
        ).run()

        last_smoke: dict[str, float] = {}
        peak_smoke: dict[str, float] = defaultdict(float)
        for line in stream.getvalue().splitlines():
            record = json.loads(line)
            last_smoke[record["device_id"]] = record["smoke_ppm"]
            peak_smoke[record["device_id"]] = max(
                peak_smoke[record["device_id"]], record["smoke_ppm"]
            )

        # Both near nodes saw the fire; the distant one stayed at baseline.
        assert peak_smoke["PYRO-T1-0001"] > 10.0
        assert peak_smoke["PYRO-T1-0002"] > 10.0
        assert peak_smoke["PYRO-T1-0003"] < 1.0
