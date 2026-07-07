"""Typed planner configuration, loadable from YAML.

Parsing and validation of user-provided configuration happen here, at
the boundary; the rest of the planner receives an already-validated
:class:`PlannerParams` value object (numeric invariants are enforced by
the components that own them: densities/jitter/slope by
``HexGridPlacement``, capacity by ``GatewayPlanner``).
"""

from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

from pyrosense_sim.planner.placement import DEFAULT_DENSITY_HA
from pyrosense_sim.planner.zones import Tier

_TIER_KEYS: dict[str, Tier] = {"t1": 1, "t2": 2, "t3": 3}


@dataclass(frozen=True)
class PlannerParams:
    """All site-planner knobs with their reasoned defaults."""

    detection_radius_m: float = 125.0
    densities_ha: dict[Tier, float] = field(default_factory=lambda: dict(DEFAULT_DENSITY_HA))
    jitter_m: float = 25.0
    max_slope_deg: float = 45.0
    seed: int = 0
    gateway_capacity: int = 60
    gateway_snap_radius_m: float = 200.0
    t1_buffer_m: float = 400.0
    zones_geojson: Path | None = None


def load_params(path: Path | None) -> PlannerParams:
    """Load parameters from a YAML file, applying defaults for absent keys.

    Args:
        path: YAML file (see ``config/params.example.yaml``), or ``None``
            for pure defaults.

    Returns:
        A validated, immutable parameter set.

    Raises:
        ValueError: If the YAML is not a mapping, contains unknown keys
            (typos fail early instead of being silently ignored) or has a
            malformed ``densities_ha`` block.
    """
    if path is None:
        return PlannerParams()
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        msg = f"planner config must be a YAML mapping, got {type(raw).__name__}"
        raise ValueError(msg)

    known = {f.name for f in fields(PlannerParams)}
    unknown = set(raw) - known
    if unknown:
        msg = f"unknown config keys {sorted(unknown)}; valid keys are {sorted(known)}"
        raise ValueError(msg)

    if "densities_ha" in raw:
        raw["densities_ha"] = _parse_densities(raw["densities_ha"])
    if "zones_geojson" in raw and raw["zones_geojson"] is not None:
        raw["zones_geojson"] = Path(raw["zones_geojson"])
    return PlannerParams(**raw)


def _parse_densities(block: object) -> dict[Tier, float]:
    """Convert the YAML ``{t1: 4, t2: 10, t3: 25}`` block to tier keys."""
    if not isinstance(block, dict) or set(block) != set(_TIER_KEYS):
        msg = f"densities_ha must map exactly t1/t2/t3 to hectares per node, got {block!r}"
        raise ValueError(msg)
    return {_TIER_KEYS[key]: float(value) for key, value in block.items()}
