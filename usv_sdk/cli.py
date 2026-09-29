"""
USV Fleet SDK — Command Line Interface & Swarm Test Harness
===========================================================
Allows operators and developers to instantiate mock USVs or full autonomous
swarms for load testing and formation validation against the Ground Station.
"""

import argparse
import math
import random
import sys
import time
from typing import List

from .agent import USVAgent
from .models import AutonomyMode, TargetPose


class MockUSV:
    """Simulated vehicle entity with local closed-loop pursuit kinetics."""

    def __init__(self, usv_id: str, x: float = 0.0, y: float = 0.0, heading: float = 0.0):
        self.usv_id = usv_id
        self.x = float(x)
        self.y = float(y)
        self.heading = float(heading)
        self.speed = 0.0
        self.max_speed = 3.5  # m/s (~7 knots)
        self.battery = 98.0
        self.target_x = self.x
        self.target_y = self.y
        self.mode = AutonomyMode.HOLD

        # Initialize SDK agent client
        self.agent = USVAgent(usv_id=self.usv_id)

        # Wire callbacks
        @self.agent.on_target_pose
        def _on_target(target: TargetPose):
            self.target_x = target.x
            self.target_y = target.y
            self.mode = AutonomyMode.FORMATION

        @self.agent.on_mode_change
        def _on_mode(mode: AutonomyMode):
            self.mode = mode

        @self.agent.on_cmd_vel
        def _on_cmd_vel(linear_x: float, angular_z: float):
            self.mode = AutonomyMode.MANUAL
            self.speed = linear_x
            self.heading += angular_z * 0.05

        @self.agent.on_emergency_stop
        def _on_estop():
            self.mode = AutonomyMode.HOLD
            self.speed = 0.0

        # Start agent background spinner
        self.agent.start_async()

    def step(self, dt: float = 0.05):
        """Step simple kinematic state machine."""
        if self.mode in (AutonomyMode.FORMATION, AutonomyMode.TRANSIT):
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)

            if dist > 1.0:
                desired_heading = math.atan2(dy, dx)
                # Heading error wrapped to [-pi, pi]
                err = (desired_heading - self.heading + math.pi) % (2.0 * math.pi) - math.pi
                turn_rate = max(-1.8, min(1.8, err * 2.2))
                self.heading += turn_rate * dt
                self.speed = min(self.max_speed, dist * 0.8)
            else:
                self.speed *= 0.8  # Arrived near target slot

        elif self.mode == AutonomyMode.HOLD:
            self.speed *= 0.85

        # Update position
        self.x += math.cos(self.heading) * self.speed * dt
        self.y += math.sin(self.heading) * self.speed * dt

        # Battery discharge simulation
        self.battery = max(5.0, self.battery - (0.001 if self.speed > 0.1 else 0.0002))

        # Synthetic sonar bottom depth (10m - 25m variation)
        sonar_depth = 18.0 + 3.0 * math.sin(self.x * 0.02) + 2.0 * math.cos(self.y * 0.02)

        # Dispatch telemetry over ROS 2 topics
        self.agent.publish_odom(
            x=self.x,
            y=self.y,
            heading=self.heading,
            speed=self.speed
        )
        self.agent.publish_battery(soc_pct=self.battery, voltage=24.2)
        self.agent.publish_sonar(range_m=sonar_depth)

    def shutdown(self):
        self.agent.shutdown()


def run_mock_single(usv_id: str, x: float, y: float):
    """Run a single mock USV node."""
    print(f"🚀 Launching mock USV '{usv_id}' at ENU coordinates ({x:.1f}, {y:.1f})...")
    print("Broadcasting on ROS 2 topics. Press Ctrl+C to stop.")
    vehicle = MockUSV(usv_id=usv_id, x=x, y=y)
    try:
        while True:
            vehicle.step(0.05)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print(f"\nShutting down {usv_id}...")
    finally:
        vehicle.shutdown()


def run_mock_swarm(count: int, spacing: float):
    """Run a swarm of N mock USVs for fleet testing."""
    print(f"🌊 Instantiating mock swarm with {count} vehicles (spacing: {spacing}m)...")
    vehicles: List[MockUSV] = []
    try:
        for i in range(1, count + 1):
            uid = f"usv_{i}"
            # Arrange in an initial staggered harbor slip
            init_x = float((i - 1) * spacing - ((count - 1) * spacing * 0.5))
            init_y = -35.0 + random.uniform(-2.0, 2.0)
            print(f"  ⚓ Spawning {uid} at ({init_x:.1f}, {init_y:.1f})")
            vehicles.append(MockUSV(usv_id=uid, x=init_x, y=init_y, heading=math.pi * 0.5))

        print(f"✅ Swarm active! Switch Ground Station to '📡 External ROS 2 / Hardware' to observe.")
        print("Press Ctrl+C to terminate the test harness.")

        while True:
            for v in vehicles:
                v.step(0.05)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopping swarm harness...")
    finally:
        for v in vehicles:
            v.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="USV Fleet SDK — CLI Swarm Test Harness & Vehicle Simulator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Mock single vehicle
    mock_parser = subparsers.add_parser("mock", help="Run a single mock USV agent")
    mock_parser.add_argument("--id", default="usv_1", help="USV identifier namespace (e.g. usv_1)")
    mock_parser.add_argument("--start-x", type=float, default=0.0, help="Initial Easting coordinate (m)")
    mock_parser.add_argument("--start-y", type=float, default=0.0, help="Initial Northing coordinate (m)")

    # Mock swarm
    swarm_parser = subparsers.add_parser("swarm", help="Run an N-vehicle autonomous swarm")
    swarm_parser.add_argument("--count", type=int, default=3, help="Number of USV agents to spawn (2 to 8)")
    swarm_parser.add_argument("--spacing", type=float, default=15.0, help="Initial vessel separation (m)")

    args = parser.parse_args()

    if args.command == "mock":
        run_mock_single(args.id, args.start_x, args.start_y)
    elif args.command == "swarm":
        run_mock_swarm(args.count, args.spacing)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
