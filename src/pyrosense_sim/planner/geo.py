"""Degree/meter conversions shared across the planner.

Single source of truth for the small-AOI approximation used everywhere
in the site-planner: one degree of latitude is treated as a constant
distance, and one degree of longitude shrinks with ``cos(lat)``. At
Bogota's latitude (~4.6 deg) the error is under 1% — see
docs/adr/ADR-0007 and the P3 design notes for when this would stop
being acceptable.
"""

from math import cos, radians

M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LON_EQUATOR = 111_320.0


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
