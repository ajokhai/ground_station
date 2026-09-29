"""
Georeference Engine for USV Ground Station.
Provides bidirectional transformations between WGS84 Geodetic coordinates
(Latitude, Longitude, Altitude) and local East-North-Up (ENU) Cartesian coordinates
relative to a configured Datum Reference Point.
"""

import math
from typing import Tuple, NamedTuple, Optional


class LatLon(NamedTuple):
    lat: float  # Decimal degrees
    lon: float  # Decimal degrees
    alt: float = 0.0  # Height above WGS84 ellipsoid in meters


class ENUCoordinate(NamedTuple):
    east: float   # X in meters
    north: float  # Y in meters
    up: float = 0.0  # Z in meters


class GeoReference:
    """
    High-precision WGS84 <-> Local ENU Georeferencing Engine.
    Uses rigorous WGS84 ellipsoidal transformations (Bowring method)
    without requiring heavy external GIS libraries (GDAL/pyproj).
    """

    # WGS-84 Ellipsoid constants
    A = 6378137.0          # Semi-major axis in meters
    F = 1.0 / 298.257223563  # Flattening
    B = A * (1.0 - F)      # Semi-minor axis (~6356752.314245)
    E_SQ = F * (2.0 - F)   # First eccentricity squared (~6.69437999014e-3)
    E_PRIME_SQ = (A**2 - B**2) / (B**2)  # Second eccentricity squared

    def __init__(self, datum_lat: float = 37.7749, datum_lon: float = -122.4194, datum_alt: float = 0.0):
        """
        Initialize with a reference datum point.
        Defaults to San Francisco Bay (37.7749° N, 122.4194° W).
        """
        self.datum_lat = datum_lat
        self.datum_lon = datum_lon
        self.datum_alt = datum_alt

        # Cache reference ECEF coordinates and rotation matrix
        self._ref_ecef = self.geodetic_to_ecef(datum_lat, datum_lon, datum_alt)
        phi = math.radians(datum_lat)
        lam = math.radians(datum_lon)
        self._sin_phi = math.sin(phi)
        self._cos_phi = math.cos(phi)
        self._sin_lam = math.sin(lam)
        self._cos_lam = math.cos(lam)

    def set_datum(self, lat: float, lon: float, alt: float = 0.0) -> None:
        """Update the base reference datum origin."""
        self.datum_lat = lat
        self.datum_lon = lon
        self.datum_alt = alt
        self._ref_ecef = self.geodetic_to_ecef(lat, lon, alt)
        phi = math.radians(lat)
        lam = math.radians(lon)
        self._sin_phi = math.sin(phi)
        self._cos_phi = math.cos(phi)
        self._sin_lam = math.sin(lam)
        self._cos_lam = math.cos(lam)

    @classmethod
    def geodetic_to_ecef(cls, lat: float, lon: float, alt: float = 0.0) -> Tuple[float, float, float]:
        """Convert WGS84 Geodetic (lat, lon, alt) to Earth-Centered, Earth-Fixed (ECEF) X, Y, Z in meters."""
        phi = math.radians(lat)
        lam = math.radians(lon)
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        sin_lam = math.sin(lam)
        cos_lam = math.cos(lam)

        # Radius of curvature in prime vertical
        n = cls.A / math.sqrt(1.0 - cls.E_SQ * (sin_phi ** 2))

        x = (n + alt) * cos_phi * cos_lam
        y = (n + alt) * cos_phi * sin_lam
        z = (n * (1.0 - cls.E_SQ) + alt) * sin_phi
        return x, y, z

    @classmethod
    def ecef_to_geodetic(cls, x: float, y: float, z: float) -> LatLon:
        """
        Convert ECEF X, Y, Z in meters back to WGS84 Geodetic (lat, lon, alt).
        Uses Bowring's closed-form method (accurate to sub-millimeter level).
        """
        p = math.sqrt(x**2 + y**2)
        if p < 1e-6:
            # Special case at Earth poles
            lat = 90.0 if z > 0 else -90.0
            lon = 0.0
            alt = abs(z) - cls.B
            return LatLon(lat, lon, alt)

        theta = math.atan2(z * cls.A, p * cls.B)
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        phi = math.atan2(
            z + cls.E_PRIME_SQ * cls.B * (sin_theta ** 3),
            p - cls.E_SQ * cls.A * (cos_theta ** 3)
        )
        lam = math.atan2(y, x)

        sin_phi = math.sin(phi)
        n = cls.A / math.sqrt(1.0 - cls.E_SQ * (sin_phi ** 2))
        alt = (p / math.cos(phi)) - n

        return LatLon(math.degrees(phi), math.degrees(lam), alt)

    def to_enu(self, lat: float, lon: float, alt: float = 0.0) -> ENUCoordinate:
        """
        Convert a WGS84 GPS coordinate (lat, lon, alt) to local East-North-Up (ENU)
        Cartesian meters relative to this engine's datum.
        """
        gx, gy, gz = self.geodetic_to_ecef(lat, lon, alt)
        dx = gx - self._ref_ecef[0]
        dy = gy - self._ref_ecef[1]
        dz = gz - self._ref_ecef[2]

        # Rotate ECEF delta to ENU frame
        east = -self._sin_lam * dx + self._cos_lam * dy
        north = -self._sin_phi * self._cos_lam * dx - self._sin_phi * self._sin_lam * dy + self._cos_phi * dz
        up = self._cos_phi * self._cos_lam * dx + self._cos_phi * self._sin_lam * dy + self._sin_phi * dz

        return ENUCoordinate(east, north, up)

    def to_latlon(self, east: float, north: float, up: float = 0.0) -> LatLon:
        """
        Convert local East-North-Up (ENU) Cartesian meters (X=East, Y=North, Z=Up)
        back to WGS84 GPS (lat, lon, alt).
        """
        # Transform ENU vector back to ECEF delta
        dx = -self._sin_lam * east - self._sin_phi * self._cos_lam * north + self._cos_phi * self._cos_lam * up
        dy = self._cos_lam * east - self._sin_phi * self._sin_lam * north + self._cos_phi * self._sin_lam * up
        dz = self._cos_phi * north + self._sin_phi * up

        gx = self._ref_ecef[0] + dx
        gy = self._ref_ecef[1] + dy
        gz = self._ref_ecef[2] + dz

        return self.ecef_to_geodetic(gx, gy, gz)

    # ── Formatting & Maritime Navigation Helpers ──

    @staticmethod
    def format_dms(lat: float, lon: float) -> str:
        """Format coordinates into Degrees-Minutes-Seconds (e.g. 37°46'29.6\"N  122°25'09.8\"W)."""
        def _dms_part(val: float, pos_char: str, neg_char: str) -> str:
            direction = pos_char if val >= 0 else neg_char
            abs_val = abs(val)
            degrees = int(abs_val)
            minutes_full = (abs_val - degrees) * 60.0
            minutes = int(minutes_full)
            seconds = (minutes_full - minutes) * 60.0
            return f"{degrees:02d}°{minutes:02d}'{seconds:04.1f}\"{direction}"

        return f"{_dms_part(lat, 'N', 'S')}  {_dms_part(lon, 'E', 'W')}"

    @staticmethod
    def format_dd(lat: float, lon: float, precision: int = 6) -> str:
        """Format coordinates into Decimal Degrees (e.g. 37.774900° N, 122.419400° W)."""
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        return f"{abs(lat):.{precision}f}° {lat_dir}, {abs(lon):.{precision}f}° {lon_dir}"

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Great-Circle distance in meters between two GPS coordinates using Haversine formula."""
        r = 6371000.0  # Mean Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def rhumb_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial compass bearing (0-360 degrees) from point 1 to point 2."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lam = math.radians(lon2 - lon1)

        y = math.sin(delta_lam) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lam)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0


def point_in_polygon(px: float, py: float, poly: list) -> bool:
    """Ray casting point-in-polygon test for 2D coordinates."""
    if len(poly) < 3:
        return False
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def dist_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> Tuple[float, float, float]:
    """
    Calculate shortest distance from point (px, py) to line segment (ax, ay)-(bx, by).
    Returns (distance, closest_x, closest_y).
    """
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    c1 = wx * vx + wy * vy
    if c1 <= 0:
        return math.hypot(px - ax, py - ay), ax, ay
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return math.hypot(px - bx, py - by), bx, by
    t = c1 / c2
    qx = ax + t * vx
    qy = ay + t * vy
    return math.hypot(px - qx, py - qy), qx, qy

