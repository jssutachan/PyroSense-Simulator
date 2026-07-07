"""Degree/meter conversions shared across the planner.

Single source of truth for the small-AOI approximation used everywhere
in the site-planner: one degree of latitude is treated as a constant
distance, and one degree of longitude shrinks with ``cos(lat)``. At
Bogota's latitude (~4.6 deg) the error is under 1% — see
docs/adr/ADR-0007 and the P3 design notes for when this would stop
being acceptable.
"""

from math import cos, hypot, radians

M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LON_EQUATOR = 111_320.0


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Planar approximate distance in meters between two lon/lat points.

    Uses the small-AOI approximation (see module docstring); do not use
    for distances where earth curvature matters.
    """
    mid_lat = (lat1 + lat2) / 2.0
    dx = (lon2 - lon1) * M_PER_DEG_LON_EQUATOR * cos(radians(mid_lat))
    dy = (lat2 - lat1) * M_PER_DEG_LAT
    return hypot(dx, dy)


def meters_to_deg_lat(meters: float) -> float:
    """Convert a north-south distance in meters to degrees of latitude."""
    return meters / M_PER_DEG_LAT


def meters_to_deg_lon(meters: float, lat: float) -> float:
    """Convert an east-west distance in meters to degrees of longitude.

    Args:
        meters: Distance in meters.
        lat: Latitude in decimal degrees where the conversion applies.

    Returns:
        The equivalent angular distance in degrees of longitude.
    """
    return meters / (M_PER_DEG_LON_EQUATOR * cos(radians(lat)))
