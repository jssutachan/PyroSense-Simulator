"""Tests for the baseline environment model (pure, deterministic physics)."""

import pytest

from pyrosense_sim.fleet.config import EnvironmentConfig
from pyrosense_sim.fleet.environment import EnvironmentModel

LON, LAT = -74.05, 4.55


def model(**overrides: float) -> EnvironmentModel:
    return EnvironmentModel(EnvironmentConfig(**overrides))


def test_temperature_peaks_at_peak_hour() -> None:
    env = model(temp_mean_c=14.0, temp_amplitude_c=6.0, temp_peak_hour=14.0)
    at_peak = env.conditions_at(LON, LAT, 2600.0, 14 * 3600.0).temp_c
    at_trough = env.conditions_at(LON, LAT, 2600.0, 2 * 3600.0).temp_c
    assert at_peak == pytest.approx(20.0)  # mean + amplitude
    assert at_trough == pytest.approx(8.0)  # mean - amplitude


def test_lapse_rate_cools_with_elevation() -> None:
    env = model(lapse_rate_c_per_km=-6.5, reference_elevation_m=2600.0)
    low = env.conditions_at(LON, LAT, 2600.0, 0.0).temp_c
    high = env.conditions_at(LON, LAT, 3600.0, 0.0).temp_c
    assert high == pytest.approx(low - 6.5)


def test_humidity_anticorrelates_with_temperature() -> None:
    env = model(rh_mean_pct=80.0, rh_amplitude_pct=15.0, temp_peak_hour=14.0)
    warmest = env.conditions_at(LON, LAT, 2600.0, 14 * 3600.0)
    coolest = env.conditions_at(LON, LAT, 2600.0, 2 * 3600.0)
    assert warmest.rh_pct < coolest.rh_pct
    assert warmest.rh_pct == pytest.approx(65.0)
    assert coolest.rh_pct == pytest.approx(95.0)


def test_humidity_is_clamped_to_valid_range() -> None:
    env = model(rh_mean_pct=95.0, rh_amplitude_pct=20.0)
    coolest = env.conditions_at(LON, LAT, 2600.0, 2 * 3600.0)
    assert coolest.rh_pct == 100.0


def test_is_deterministic() -> None:
    env = model()
    first = env.conditions_at(LON, LAT, 2800.0, 12345.0)
    second = env.conditions_at(LON, LAT, 2800.0, 12345.0)
    assert first == second


def test_cycle_repeats_every_24_hours() -> None:
    env = model()
    day_one = env.conditions_at(LON, LAT, 2800.0, 5 * 3600.0)
    day_two = env.conditions_at(LON, LAT, 2800.0, (24 + 5) * 3600.0)
    assert day_one.temp_c == pytest.approx(day_two.temp_c)
