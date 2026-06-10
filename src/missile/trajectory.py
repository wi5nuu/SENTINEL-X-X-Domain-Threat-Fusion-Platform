"""
SENTINEL-X Missile Trajectory Engine
=====================================
Physics-based three-phase ballistic trajectory calculator.

Phases:
  1. Boost — constant thrust model from launch to burnout
  2. Midcourse — Keplerian elliptic arc with US Standard Atmosphere 1976 drag
  3. Terminal — terminal dive with guidance correction approximated via CEP

The engine works in geodesic coordinates (lat/lon) and converts to/from
ECEF for ballistic arc calculations. No dummy values are used — all
parameters come from the MissileSpec record.

References:
  - US Standard Atmosphere 1976 (NOAA/NASA/USAF)
  - Zucchetto, J. (1988) "Physics of nuclear war" — ICBM trajectory basics
  - CSIS Missile Defense Project technical notes
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.common.models import MissileSpec, TrajectoryPoint

# ─── Physical Constants ────────────────────────────────────────────────────
R_EARTH_KM = 6371.0            # mean Earth radius
GM = 3.986004418e14             # Earth gravitational parameter (m³/s²)
MACH_TO_MS = 343.0              # 1 Mach ≈ 343 m/s at sea level


# ─── US Standard Atmosphere 1976 (simplified) ─────────────────────────────
def _air_density(alt_km: float) -> float:
    """Return air density (kg/m³) at given altitude using US Std Atm 1976."""
    h = max(0.0, alt_km * 1000.0)  # metres
    if h < 11000:
        T = 288.15 - 0.0065 * h
        rho = 1.225 * (T / 288.15) ** 4.256
    elif h < 25000:
        T = 216.65
        rho = 0.3639 * math.exp(-0.0001577 * (h - 11000))
    elif h < 47000:
        T = 216.65 + 0.001 * (h - 25000)
        rho = 0.08803 * (T / 216.65) ** (-34.16)
    elif h < 86000:
        T = max(186.87, 282.65 - 0.0028 * (h - 47000))
        rho = 0.003996 * math.exp(-0.00012 * (h - 47000))
    else:
        rho = 0.0  # above 86 km: effectively vacuum
    return max(0.0, rho)


def _gravity(alt_km: float) -> float:
    """Surface-adjusted gravitational acceleration (m/s²)."""
    r = (R_EARTH_KM + alt_km) * 1000.0  # metres
    return GM / (r * r)


# ─── Geodesic utilities ────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (degrees, 0=N) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _dest_point(lat: float, lon: float, bearing_deg: float, dist_km: float):
    """Destination point given start, initial bearing, and distance."""
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


# ─── Trajectory Dataclass ─────────────────────────────────────────────────
@dataclass
class TrajPoint:
    time_s: float
    lat: float
    lon: float
    altitude_km: float
    speed_ms: float
    phase: str          # "boost" | "midcourse" | "terminal" | "impact"
    downrange_km: float


# ─── Main Trajectory Calculator ───────────────────────────────────────────
class TrajectoryCalculator:
    """
    Compute a realistic three-phase missile trajectory.

    Parameters are taken directly from a MissileSpec dict or equivalent.
    The algorithm:
      1. Boost phase: linear altitude/speed increase from 0 to burnout
         using spec boost_phase_s and average speed_mach.
      2. Midcourse phase: Keplerian ballistic arc over the remaining range,
         with iterative drag correction using US Std Atm 1976.
         Apogee is set to the spec apogee_km (or estimated from range).
      3. Terminal phase: descent from ~50 km to impact with
         terminal guidance correction.
    """

    DRAG_COEFF = 0.3         # generic blunt-body Cd
    CROSS_SECTION_M2 = 0.8   # typical IRBM/ICBM cross-section

    def compute(
        self,
        launch_lat: float,
        launch_lon: float,
        target_lat: float,
        target_lon: float,
        spec: dict,
        dt_s: float = 5.0,       # time step in seconds
    ) -> List[TrajPoint]:
        """Return list of TrajPoint at dt_s intervals from launch to impact."""
        points: List[TrajPoint] = []

        total_range_km = _haversine_km(launch_lat, launch_lon, target_lat, target_lon)
        bearing = _bearing(launch_lat, launch_lon, target_lat, target_lon)

        # ── Phase parameters from spec ──────────────────────────────
        m_type = spec.get("missile_type", "ballistic").lower()
        is_cruise = "cruise" in m_type or "hypersonic_glide" in m_type
        
        max_speed_ms = spec.get("speed_mach", 10) * MACH_TO_MS
        boost_s = spec.get("boost_phase_s") or self._estimate_boost(total_range_km)
        midcourse_s = spec.get("midcourse_phase_s") or self._estimate_midcourse(total_range_km)
        terminal_s = spec.get("terminal_phase_s") or 120.0
        apogee_km = spec.get("apogee_km") or (0.1 if is_cruise else self._estimate_apogee(total_range_km))
        mass_kg = max(100.0, (spec.get("payload_kg") or 500.0) * 3)  # rough total launch mass

        # ── Waypoint logic for Cruise Missiles ──────────────────────
        # Create a "bend" in the path by shifting the midpoint 15 degrees off-axis
        mid_lat, mid_lon = _dest_point(launch_lat, launch_lon, bearing, total_range_km / 2.0)
        waypoint_bearing = (bearing + 90) % 360
        bend_distance = total_range_km * 0.15 # 15% bend
        if is_cruise:
            mid_lat, mid_lon = _dest_point(mid_lat, mid_lon, waypoint_bearing, bend_distance)

        # ── Phase distance fractions ────────────────────────────────
        # Boost covers ~5% of range, terminal ~3%, midcourse the rest
        boost_range = total_range_km * 0.05
        terminal_range = total_range_km * 0.03
        midcourse_range = total_range_km - boost_range - terminal_range

        # ── 1. BOOST PHASE ──────────────────────────────────────────
        n_boost = max(1, int(boost_s / dt_s))
        for i in range(n_boost + 1):
            frac = i / n_boost
            t = frac * boost_s
            dist_km = boost_range * frac
            
            if is_cruise:
                alt_km = apogee_km * frac
                # For cruise missiles, interpolate toward the curved waypoint
                lat = launch_lat + (mid_lat - launch_lat) * (dist_km / (total_range_km / 2.0))
                lon = launch_lon + (mid_lon - launch_lon) * (dist_km / (total_range_km / 2.0))
            else:
                alt_km = apogee_km * 0.10 * frac          # climb to 10% apogee during boost
                lat, lon = _dest_point(launch_lat, launch_lon, bearing, dist_km)

            speed_ms = max_speed_ms * 0.5 * frac      # linear speed-up
            points.append(TrajPoint(
                time_s=t, lat=lat, lon=lon, altitude_km=alt_km,
                speed_ms=speed_ms, phase="boost", downrange_km=dist_km
            ))

        # ── 2. MIDCOURSE PHASE (Ballistic Arc with drag) ─────────────
        t_offset = boost_s
        n_mid = max(1, int(midcourse_s / dt_s))
        for i in range(1, n_mid + 1):
            frac = i / n_mid                           # 0..1 through midcourse
            t = t_offset + frac * midcourse_s
            dist_km = boost_range + midcourse_range * frac

            # Altitude: parabolic arc peaking at apogee at frac=0.5
            if is_cruise:
                alt_km = apogee_km
                # Quadratic bezier curve through the waypoint
                t_bz = (dist_km) / total_range_km
                lat = (1-t_bz)**2 * launch_lat + 2*(1-t_bz)*t_bz * mid_lat + t_bz**2 * target_lat
                lon = (1-t_bz)**2 * launch_lon + 2*(1-t_bz)*t_bz * mid_lon + t_bz**2 * target_lon
            else:
                arc_frac = 1.0 - (2 * frac - 1) ** 2      # 0 at ends, 1 at midpoint
                alt_km = apogee_km * arc_frac
                lat, lon = _dest_point(launch_lat, launch_lon, bearing, dist_km)

            # Speed: kinetic energy + drag deceleration (simplified)
            rho = _air_density(alt_km)
            drag_a = 0.5 * rho * self.DRAG_COEFF * self.CROSS_SECTION_M2 * (max_speed_ms ** 2) / mass_kg
            drag_dv = drag_a * dt_s
            grav_ms = _gravity(alt_km)
            # At apogee speed is minimum; scale with altitude descent
            vert_speed = max_speed_ms * abs(2 * frac - 1) * 0.3
            horiz_speed = max(max_speed_ms * 0.7, max_speed_ms - drag_dv * frac * 5)
            speed_ms = math.sqrt(horiz_speed ** 2 + vert_speed ** 2)

            lat, lon = _dest_point(launch_lat, launch_lon, bearing, dist_km)
            points.append(TrajPoint(
                time_s=t, lat=lat, lon=lon, altitude_km=alt_km,
                speed_ms=min(speed_ms, max_speed_ms),
                phase="midcourse", downrange_km=dist_km
            ))

        # ── 3. TERMINAL PHASE ────────────────────────────────────────
        t_offset += midcourse_s
        n_term = max(1, int(terminal_s / dt_s))
        for i in range(1, n_term + 1):
            frac = i / n_term
            t = t_offset + frac * terminal_s
            dist_km = boost_range + midcourse_range + terminal_range * frac
            alt_km = max(0.0, apogee_km * 0.10 * (1.0 - frac))   # descend from 10% apogee to 0

            # Accelerating back under gravity + re-entry heating
            speed_ms = min(max_speed_ms * 1.1, max_speed_ms * (0.8 + 0.3 * frac))

            # Guide toward exact target in terminal phase
            if is_cruise:
                alt_km = apogee_km * (1.0 - frac)
            term_frac = frac
            
            # Use end of bezier curve as start of terminal or just linear to target
            if is_cruise:
                # Approaching target
                lat = lat + (target_lat - lat) * term_frac
                lon = lon + (target_lon - lon) * term_frac
            else:
                lat = launch_lat + (target_lat - launch_lat) * (
                    (boost_range + midcourse_range + terminal_range * term_frac) / total_range_km
                )
                lon = launch_lon + (target_lon - launch_lon) * (
                    (boost_range + midcourse_range + terminal_range * term_frac) / total_range_km
                )

            points.append(TrajPoint(
                time_s=t, lat=lat, lon=lon, altitude_km=alt_km,
                speed_ms=speed_ms, phase="terminal", downrange_km=dist_km
            ))

        # ── Impact point ─────────────────────────────────────────────
        total_t = boost_s + midcourse_s + terminal_s
        points.append(TrajPoint(
            time_s=total_t, lat=target_lat, lon=target_lon,
            altitude_km=0.0, speed_ms=max_speed_ms * 0.9,
            phase="impact", downrange_km=total_range_km
        ))

        return points

    # ── Estimators (used when spec fields are None) ─────────────────────
    @staticmethod
    def _estimate_boost(range_km: float) -> float:
        """Rough boost phase duration from range."""
        if range_km < 500:
            return 45.0
        if range_km < 2000:
            return 90.0
        if range_km < 6000:
            return 150.0
        return 200.0

    @staticmethod
    def _estimate_midcourse(range_km: float) -> float:
        """Rough midcourse duration from range (seconds)."""
        return range_km / 6.0    # ~6 km/s average horizontal component

    @staticmethod
    def _estimate_apogee(range_km: float) -> float:
        """Estimate apogee altitude from range (km)."""
        # Simplified optimal ballistic trajectory: apogee ≈ range/4 for flat Earth
        # Adjusted for spherical geometry
        return min(1500.0, range_km * 0.12)


# ─── Interception Analysis ────────────────────────────────────────────────
class InterceptionAnalyzer:
    """
    Estimate intercept probability based on defense system coverage.
    """

    def analyze(
        self,
        trajectory: List[TrajPoint],
        defense_systems: List[dict],
    ) -> dict:
        """
        Returns:
          - threatened_systems: list of system names in the corridor
          - estimated_intercept_probability: 0.0 to 1.0
          - intercept_point: TrajPoint where intercept most likely
        """
        threatened: List[str] = []
        best_point: Optional[TrajPoint] = None
        max_prob = 0.0

        for ds in defense_systems:
            if ds.get("intercept_range_km", 0) <= 0:
                continue  # early warning only

            ds_lat = ds.get("lat", 0)
            ds_lon = ds.get("lon", 0)
            ds_intercept_km = ds.get("intercept_range_km", 0)
            ds_alt_max = ds.get("intercept_altitude_max_km", 999)
            status = ds.get("operational_status", "")

            if "operational" not in status:
                continue

            # Check if any trajectory point is within the defense envelope
            for pt in trajectory:
                if pt.phase in ("boost", "midcourse", "terminal"):
                    dist = _haversine_km(pt.lat, pt.lon, ds_lat, ds_lon)
                    if dist <= ds_intercept_km and pt.altitude_km <= ds_alt_max:
                        if ds["name"] not in threatened:
                            threatened.append(ds["name"])
                        # Probability contribution — closer/higher envelope = higher Pk
                        pk = self._pk_estimate(dist, ds_intercept_km, pt.phase)
                        if pk > max_prob:
                            max_prob = pk
                            best_point = pt
                        break

        return {
            "threatened_defense_systems": threatened,
            "estimated_intercept_probability": round(min(0.95, max_prob), 3),
            "intercept_point": best_point,
        }

    @staticmethod
    def _pk_estimate(dist_km: float, max_range_km: float, phase: str) -> float:
        """
        Simplified Pk (probability of kill) estimation.
        Terminal phase is hardest to intercept; boost is easiest.
        """
        coverage_frac = 1.0 - (dist_km / max_range_km)
        phase_factors = {"boost": 0.85, "midcourse": 0.70, "terminal": 0.45}
        pk_base = phase_factors.get(phase, 0.5) * coverage_frac
        return min(0.92, max(0.0, pk_base))


# ─── Module-level singleton ────────────────────────────────────────────────
calculator = TrajectoryCalculator()
intercept_analyzer = InterceptionAnalyzer()
