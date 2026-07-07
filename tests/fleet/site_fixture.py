"""Helper to write minimal sensores.geojson files for fleet tests."""

import json
from pathlib import Path


def write_site(path: Path, node_count: int = 3) -> Path:
    """Write a tiny site plan with ``node_count`` T1 nodes and one gateway.

    Node ``PYRO-T1-0001`` carries a wind sensor; the rest do not.
    """
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-74.05 + 0.001 * index, 4.55],
            },
            "properties": {
                "device_id": f"PYRO-T1-{index + 1:04d}",
                "tier": 1,
                "zone_name": "test",
                "elevation_m": 2800.0 + 50.0 * index,
                "slope_deg": 5.0,
                "gateway_id": "GW-01",
                "has_wind_sensor": index == 0,
            },
        }
        for index in range(node_count)
    ]
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
    )
    return path
