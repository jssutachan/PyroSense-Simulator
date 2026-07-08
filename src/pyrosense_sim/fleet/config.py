"""Scenario configuration for the fleet simulator.

A scenario YAML is **user input crossing the process boundary**, so it
gets pydantic validation (ADR-0003): strict types, physical ranges and
``extra="forbid"`` — a typo in a key is an error, never a silently
ignored setting.

Example:
    >>> config = load_scenario(Path("scenarios/baseline.yaml"))  # doctest: +SKIP
    >>> config.environment.temp_mean_c  # doctest: +SKIP
    13.0
"""

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EnvironmentConfig(BaseModel):
    """Baseline environment parameters (fire events are configured separately)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    temp_mean_c: float = 14.0
    temp_amplitude_c: float = Field(default=6.0, ge=0.0)
    temp_peak_hour: float = Field(default=14.0, ge=0.0, lt=24.0)
    lapse_rate_c_per_km: float = -6.5
    reference_elevation_m: float = 2600.0
    rh_mean_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    rh_amplitude_pct: float = Field(default=15.0, ge=0.0, le=100.0)
    wind_speed_mean_ms: float = Field(default=2.5, ge=0.0)
    wind_dir_mean_deg: float = Field(default=90.0, ge=0.0, le=360.0)
    smoke_baseline_ppm: float = Field(default=0.02, ge=0.0)


class NodeConfig(BaseModel):
    """Per-node behavior: sampling cadence, battery, sensor noise, thresholds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    t_normal_s: float = Field(default=300.0, gt=0.0)
    t_alert_s: float = Field(default=30.0, gt=0.0)
    alert_temp_c: float = 28.0
    alert_smoke_ppm: float = 4.0
    battery_start_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    battery_drain_pct_per_day: float = Field(default=1.0, ge=0.0)
    low_battery_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    degraded_battery_pct: float = Field(default=10.0, ge=0.0, le=100.0)
    sigma_temp_c: float = Field(default=0.3, ge=0.0)
    sigma_rh_pct: float = Field(default=2.0, ge=0.0)
    sigma_smoke_ppm: float = Field(default=0.01, ge=0.0)
    sigma_wind_ms: float = Field(default=0.4, ge=0.0)
    sigma_wind_dir_deg: float = Field(default=10.0, ge=0.0)


class WindBiasConfig(BaseModel):
    """Directional drift of a fire's effective center, in meters per minute."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    east_m_per_min: float = 0.0
    north_m_per_min: float = 0.0


class FireEventConfig(BaseModel):
    """One parametric fire event (interpolation, NOT physics — see ADR-0011)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    epicenter_lon: float = Field(ge=-180.0, le=180.0)
    epicenter_lat: float = Field(ge=-90.0, le=90.0)
    start_hour: float = Field(ge=0.0)
    initial_radius_m: float = Field(gt=0.0)
    growth_rate_m_per_min: float = Field(default=0.0, ge=0.0)
    wind_bias: WindBiasConfig = WindBiasConfig()
    ramp_minutes: float = Field(default=20.0, gt=0.0)
    halo_m: float = Field(default=200.0, ge=0.0)
    peak_temp_delta_c: float = Field(default=25.0, ge=0.0)
    peak_rh_drop_pct: float = Field(default=30.0, ge=0.0)
    peak_smoke_ppm: float = Field(default=40.0, ge=0.0)


class NodeDropoutConfig(BaseModel):
    """A fraction of nodes goes silent during periodic windows."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fraction: float = Field(gt=0.0, le=1.0)
    period_min: float = Field(default=60.0, gt=0.0)
    window_min: float = Field(default=15.0, gt=0.0)

    @model_validator(mode="after")
    def _window_fits_period(self) -> "NodeDropoutConfig":
        if self.window_min > self.period_min:
            msg = "window_min cannot exceed period_min"
            raise ValueError(msg)
        return self


class BurstReconnectConfig(BaseModel):
    """A device or a whole gateway goes offline, then replays its backlog in a burst."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    device_id: str | None = None
    gateway_id: str | None = None
    offline_from_hour: float = Field(ge=0.0)
    offline_hours: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "BurstReconnectConfig":
        if (self.device_id is None) == (self.gateway_id is None):
            msg = "set exactly one of device_id or gateway_id"
            raise ValueError(msg)
        return self


class DuplicatesConfig(BaseModel):
    """Random re-delivery with the same seq (MQTT QoS 1 at-least-once)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    probability: float = Field(default=0.05, gt=0.0, le=1.0)


class OutOfOrderConfig(BaseModel):
    """Local permutation of the emission order within a sliding window."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    window: int = Field(default=4, ge=2)


class BatteryDecayConfig(BaseModel):
    """Accelerated battery drain rewritten onto the message stream."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extra_pct_per_day: float = Field(gt=0.0)
    low_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    degraded_pct: float = Field(default=10.0, ge=0.0, le=100.0)


class LoadConfig(BaseModel):
    """Load-test controls: replicate the fleet to stress the ingestion pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fleet_multiplier: int = Field(default=1, ge=1)


class FaultsConfig(BaseModel):
    """Which faults the injector applies; ``None`` disables a fault."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_dropout: NodeDropoutConfig | None = None
    burst_reconnect: BurstReconnectConfig | None = None
    duplicates: DuplicatesConfig | None = None
    out_of_order: OutOfOrderConfig | None = None
    battery_decay: BatteryDecayConfig | None = None


class ScenarioConfig(BaseModel):
    """A complete, validated simulation scenario."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str = ""
    start_time: datetime = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    duration_hours: float = Field(default=24.0, gt=0.0)
    seed: int = 0
    environment: EnvironmentConfig = EnvironmentConfig()
    node: NodeConfig = NodeConfig()
    fires: list[FireEventConfig] = Field(default_factory=list)
    faults: FaultsConfig | None = None
    load: LoadConfig = LoadConfig()

    @field_validator("start_time")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            msg = "start_time must be timezone-aware (telemetry timestamps derive from it)"
            raise ValueError(msg)
        return value.astimezone(UTC)

    @property
    def duration_s(self) -> float:
        """Scenario duration in simulated seconds."""
        return self.duration_hours * 3600.0


def load_scenario(path: Path) -> ScenarioConfig:
    """Load and validate a scenario YAML.

    Args:
        path: Scenario file (see ``scenarios/baseline.yaml``).

    Returns:
        The validated scenario.

    Raises:
        ValueError: If the YAML is not a mapping.
        pydantic.ValidationError: If any field is invalid or unknown.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"scenario file {path} must contain a YAML mapping"
        raise ValueError(msg)
    return ScenarioConfig.model_validate(raw)
