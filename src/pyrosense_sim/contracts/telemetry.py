"""Telemetry data contract, payload v1 (FROZEN).

This model is the wire agreement between the simulator and the cloud
backend. Once published as v1 it must not change: additive evolution
requires a new ``schema_version``, never edits to existing fields.

Design decision — "alerting is not the sensor's responsibility":
``status`` reports **device health** (power, sensor degradation), never a
fire signal. Fire detection is inferred in the cloud from the raw
measurements (``temp_c``, ``smoke_ppm``, ``rh_pct``...). A field node has
neither the context (neighbours, wind, history) nor the compute budget to
make that call, and duplicating the decision in two places would create
contradictory alerts.

Notes:
- ``seq`` is a per-device monotonic counter. The model validates the type
  and sign; monotonicity across messages is enforced by the consumer.
- ``wind_speed_ms`` / ``wind_dir_deg`` are ``None`` when the node has no
  wind sensor. The keys are always present in the serialized payload
  (``null``, never omitted) so downstream parsers see a stable shape.
- ``ts_device`` must be timezone-aware; it is normalized to UTC and always
  serializes as ISO 8601 with a ``Z`` suffix.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class DeviceStatus(StrEnum):
    """Device health status. Not a fire signal (see module docstring)."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    LOW_BATTERY = "LOW_BATTERY"


class TelemetryPayload(BaseModel):
    """Flat (non-nested) telemetry payload, contract v1.

    Instances are immutable (``frozen``) and reject unknown fields
    (``extra="forbid"``): a v1 producer can never silently emit something
    a v1 consumer does not understand.

    Example:
        >>> from datetime import UTC, datetime
        >>> payload = TelemetryPayload(
        ...     device_id="PYRO-T1-0042",
        ...     gateway_id="GW-01",
        ...     ts_device=datetime(2026, 7, 7, 12, 30, tzinfo=UTC),
        ...     seq=7,
        ...     lat=4.6097, lon=-74.04, elevation_m=3050.0,
        ...     temp_c=18.5, rh_pct=65.0, smoke_ppm=0.02,
        ...     wind_speed_ms=None, wind_dir_deg=None,
        ...     battery_pct=88.0, status=DeviceStatus.OK,
        ... )
        >>> payload.model_dump_json()[:31]
        '{"schema_version":"1.0","device'
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    device_id: str = Field(pattern=r"^PYRO-T[123]-\d{4}$")
    gateway_id: str = Field(pattern=r"^GW-\d{2,}$")
    ts_device: datetime
    seq: int = Field(ge=0)
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    elevation_m: float
    temp_c: float = Field(ge=-20.0, le=80.0)
    rh_pct: float = Field(ge=0.0, le=100.0)
    smoke_ppm: float = Field(ge=0.0)
    wind_speed_ms: float | None = Field(ge=0.0)
    wind_dir_deg: float | None = Field(ge=0.0, le=360.0)
    battery_pct: float = Field(ge=0.0, le=100.0)
    status: DeviceStatus

    @field_validator("ts_device")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            msg = "ts_device must be timezone-aware; naive datetimes are ambiguous on the wire"
            raise ValueError(msg)
        return value.astimezone(UTC)

    @field_serializer("ts_device")
    def _serialize_ts_device(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
