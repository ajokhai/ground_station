"""
USV Fleet Python SDK (usv_sdk)
==============================
A lightweight, high-performance ROS 2 client SDK for connecting physical
Unmanned Surface Vehicles (USVs), companion computers, and marine simulation
engines to the USV Ground Station.
"""

from .agent import USVAgent
from .models import AutonomyMode, TelemetryState, TargetPose, MarineObstacle

__version__ = "0.1.0"
__all__ = [
    "USVAgent",
    "AutonomyMode",
    "TelemetryState",
    "TargetPose",
    "MarineObstacle",
]
