"""
Data models and typed structures for the USV Fleet Python SDK.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Optional, List, Tuple


class AutonomyMode(str, Enum):
    """Operational autonomy modes commanded by the Ground Station."""
    FORMATION = "FORMATION"
    TRANSIT = "TRANSIT"
    HOLD = "HOLD"
    RTH = "RTH"
    MANUAL = "MANUAL"
    AVOIDING = "AVOIDING"


@dataclass
class TelemetryState:
    """Kinematic state of a USV in local ENU (East-North-Up) coordinates."""
    x: float = 0.0              # Easting (meters)
    y: float = 0.0              # Northing (meters)
    z: float = 0.0              # Altitude / depth (meters)
    heading: float = 0.0        # True yaw angle in radians (0 = East, pi/2 = North)
    speed: float = 0.0          # Linear surge velocity (m/s)
    sway_speed: float = 0.0     # Lateral sway velocity (m/s)
    yaw_rate: float = 0.0       # Yaw rate (rad/s)
    battery_pct: float = 100.0  # Battery state of charge (0.0 - 100.0%)
    voltage: float = 24.0       # Bus voltage (Volts)
    sonar_depth_m: float = 12.0 # Sounder reading (meters)
    timestamp: float = 0.0

    @property
    def heading_deg(self) -> float:
        """Returns heading in degrees [0, 360)."""
        deg = math.degrees(self.heading) % 360.0
        return deg if deg >= 0 else deg + 360.0

    def to_quaternion(self) -> Tuple[float, float, float, float]:
        """Convert planar heading yaw to quaternion (qx, qy, qz, qw)."""
        half_yaw = self.heading * 0.5
        return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


@dataclass
class TargetPose:
    """Downlink target waypoint or assigned formation slot from Ground Station."""
    x: float
    y: float
    heading: float = 0.0
    slot_id: int = 0
    frame_id: str = "world"

    @property
    def heading_deg(self) -> float:
        return math.degrees(self.heading) % 360.0


@dataclass
class MarineObstacle:
    """Navigational obstacle detected or cataloged in the maritime theater."""
    x: float
    y: float
    radius: float = 5.0
    label: str = "HAZARD"
    confidence: float = 1.0


def quaternion_to_yaw(qx: float, qy: float, qz: float, qw: float) -> float:
    """Extract planar yaw angle (radians) from quaternion."""
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny_cosp, cosy_cosp)
