"""Validation and serialization tests for the v1 telemetry contract."""

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from pyrosense_sim.contracts.telemetry import DeviceStatus, TelemetryPayload


def valid_kwargs(**overrides: Any) -> dict[str, Any]:
    """Baseline valid payload (a T1 node on the Cerros Orientales) plus overrides."""
    base: dict[str, Any] = {
        "device_id": "PYRO-T1-0042",
        "gateway_id": "GW-01",
        "ts_device": datetime(2026, 7, 7, 12, 30, 0, tzinfo=UTC),
        "seq": 7,
        "lat": 4.6097,
        "lon": -74.0400,
        "elevation_m": 3050.0,
        "temp_c": 18.5,
        "rh_pct": 65.0,
        "smoke_ppm": 0.02,
        "wind_speed_ms": 3.4,
        "wind_dir_deg": 270.0,
        "battery_pct": 88.0,
        "status": DeviceStatus.OK,
    }
    base.update(overrides)
    return base


class TestValidPayload:
    def test_builds_and_roundtrips(self) -> None:
        payload = TelemetryPayload(**valid_kwargs())
        parsed = json.loads(payload.model_dump_json())
        assert parsed["schema_version"] == "1.0"
        assert parsed["device_id"] == "PYRO-T1-0042"
        assert parsed["status"] == "OK"
        # The serialized payload must validate against the model itself.
        assert TelemetryPayload.model_validate(parsed) == payload

    def test_ts_device_serializes_with_z_suffix(self) -> None:
        payload = TelemetryPayload(**valid_kwargs())
        parsed = json.loads(payload.model_dump_json())
        assert parsed["ts_device"] == "2026-07-07T12:30:00Z"

    def test_non_utc_timezone_is_normalized_to_utc(self) -> None:
        bogota = timezone(timedelta(hours=-5))
        payload = TelemetryPayload(
            **valid_kwargs(ts_device=datetime(2026, 7, 7, 7, 30, 0, tzinfo=bogota))
        )
        parsed = json.loads(payload.model_dump_json())
        assert parsed["ts_device"] == "2026-07-07T12:30:00Z"

    def test_payload_is_immutable(self) -> None:
        payload = TelemetryPayload(**valid_kwargs())
        with pytest.raises(ValidationError):
            payload.temp_c = 99.0  # type: ignore[misc]


class TestWindOptionality:
    def test_none_wind_is_valid_and_serializes_as_null(self) -> None:
        payload = TelemetryPayload(**valid_kwargs(wind_speed_ms=None, wind_dir_deg=None))
        parsed = json.loads(payload.model_dump_json())
        # Keys must be present with null, never omitted: stable shape downstream.
        assert "wind_speed_ms" in parsed
        assert "wind_dir_deg" in parsed
        assert parsed["wind_speed_ms"] is None
        assert parsed["wind_dir_deg"] is None

    def test_wind_keys_are_required_even_if_nullable(self) -> None:
        kwargs = valid_kwargs()
        del kwargs["wind_speed_ms"]
        with pytest.raises(ValidationError):
            TelemetryPayload(**kwargs)


class TestValidationRules:
    @pytest.mark.parametrize(
        ("field", "bad_value"),
        [
            ("schema_version", "2.0"),
            ("device_id", "PYRO-T4-0001"),  # tier 4 no existe
            ("device_id", "PYRO-T1-42"),  # serial de menos de 4 dígitos
            ("gateway_id", "GW-1"),  # requiere al menos 2 dígitos
            ("ts_device", datetime(2026, 7, 7, 12, 30, 0)),  # naive: sin timezone
            ("seq", -1),
            ("lat", 91.0),
            ("lon", -181.0),
            ("temp_c", 120.0),
            ("temp_c", -40.0),
            ("rh_pct", 100.1),
            ("rh_pct", -0.1),
            ("smoke_ppm", -1.0),
            ("wind_speed_ms", -0.5),
            ("wind_dir_deg", 360.5),
            ("battery_pct", 101.0),
            ("status", "ON_FIRE"),  # la alerta no es responsabilidad del sensor
        ],
    )
    def test_rejects_invalid_value(self, field: str, bad_value: Any) -> None:
        with pytest.raises(ValidationError):
            TelemetryPayload(**valid_kwargs(**{field: bad_value}))

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            TelemetryPayload(**valid_kwargs(fire_alert=True))
