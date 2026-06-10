"""
SENTINEL-X Missile Range Calculator
=====================================
Computes reachable-area polygons (range rings) and target-set analysis
for a given missile from a given launch point.

All calculations use geodesic geometry on the WGS84 ellipsoid approximated
as a sphere of radius 6371 km. Polygons are returned as lists of
(lat, lon) tuples suitable for DeckGL GeoJsonLayer or Leaflet.
"""

from __future__ import annotations

import math
from typing import List, Tuple

R_EARTH_KM = 6371.0

import yaml
from pathlib import Path

# Load country centroids from backend yaml config
_osint_config_path = Path(__file__).parent.parent.parent / "data" / "missile_intel" / "osint_config.yaml"
try:
    with open(_osint_config_path, "r", encoding="utf-8") as _f:
        _osint_config = yaml.safe_load(_f)
        _raw_centroids = _osint_config.get("country_centroids", {})
        COUNTRY_CENTROIDS = {k: tuple(v) for k, v in _raw_centroids.items()}
except Exception as e:
    import logging
    logging.getLogger("range-calculator").error(f"Failed to load osint_config.yaml for centroids: {e}")
    COUNTRY_CENTROIDS = {}


def _dest_point(lat: float, lon: float, bearing_deg: float, dist_km: float) -> Tuple[float, float]:
    """Destination point given start lat/lon, bearing, and distance (km)."""
    angular = dist_km / R_EARTH_KM
    b = math.radians(bearing_deg)
    phi1, lam1 = math.radians(lat), math.radians(lon)
    phi2 = math.asin(
        math.sin(phi1) * math.cos(angular)
        + math.cos(phi1) * math.sin(angular) * math.cos(b)
    )
    lam2 = lam1 + math.atan2(
        math.sin(b) * math.sin(angular) * math.cos(phi1),
        math.cos(angular) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), math.degrees(lam2)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def compute_range_ring(
    launch_lat: float,
    launch_lon: float,
    range_km: float,
    n_points: int = 72,  # every 5 degrees
) -> List[Tuple[float, float]]:
    """
    Return a geodesic circle polygon as list of (lat, lon) tuples.
    The ring represents the maximum range boundary of a missile.
    """
    ring = []
    for i in range(n_points + 1):
        bearing = (i / n_points) * 360.0
        lat, lon = _dest_point(launch_lat, launch_lon, bearing, range_km)
        ring.append((lat, lon))
    return ring


def compute_coverage_zones(
    launch_lat: float,
    launch_lon: float,
    max_range_km: float,
    min_range_km: float = 0.0,
    n_rings: int = 4,
    n_points: int = 72,
) -> List[dict]:
    """
    Return multiple concentric range zones for visualization:
    Each zone has a color based on threat proximity.
    Returns list of dicts with: range_km, ring_points, color
    """
    zones = []
    ring_ranges = []

    # Create evenly-spaced rings between min and max range
    if min_range_km > 0:
        ring_ranges.append(min_range_km)
    step = (max_range_km - min_range_km) / n_rings
    for i in range(1, n_rings + 1):
        ring_ranges.append(min_range_km + step * i)

    # Color gradient: close ranges red, far ranges amber
    colors = [
        "#FF1A1A",  # inner — immediate threat
        "#FF6B00",  # medium-close
        "#FFB800",  # medium-far
        "#4DA3FF",  # outer — max range
        "#1A5CFF",  # extended
    ]

    for idx, range_km in enumerate(ring_ranges):
        color = colors[min(idx, len(colors) - 1)]
        ring = compute_range_ring(launch_lat, launch_lon, range_km, n_points)
        zones.append({
            "range_km": range_km,
            "ring": ring,
            "color": color,
            "is_max_range": range_km >= max_range_km * 0.99,
            "is_min_range": range_km <= min_range_km * 1.01,
        })

    return zones


def countries_in_range(
    launch_lat: float,
    launch_lon: float,
    range_km: float,
) -> List[dict]:
    """
    Return list of country centroids within missile range.
    Uses approximate centroids — not precise border analysis.
    """
    within = []
    for iso3, (clat, clon) in COUNTRY_CENTROIDS.items():
        dist = _haversine_km(launch_lat, launch_lon, clat, clon)
        if dist <= range_km:
            within.append({
                "country": iso3,
                "centroid_lat": clat,
                "centroid_lon": clon,
                "distance_km": round(dist, 1),
                "within_range": True,
            })
    within.sort(key=lambda x: x["distance_km"])
    return within


def flight_time_estimate(
    range_km: float,
    speed_mach: float,
    boost_phase_s: float = 0.0,
    midcourse_phase_s: float = 0.0,
    terminal_phase_s: float = 0.0,
) -> float:
    """
    Estimate total flight time in seconds.
    If phase durations are provided, use sum; otherwise use range/speed.
    """
    if boost_phase_s and midcourse_phase_s and terminal_phase_s:
        return boost_phase_s + midcourse_phase_s + terminal_phase_s
    avg_speed_ms = speed_mach * 343.0 * 0.7  # horizontal component ~70% of total
    return range_km * 1000.0 / max(1.0, avg_speed_ms)
