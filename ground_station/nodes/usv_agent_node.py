"""
USV Reference Agent Node
========================
A reference autonomous vehicle node built using the `usv_sdk`.
Suitable for onboard execution on companion computers (NVIDIA Jetson, Raspberry Pi)
or desktop robotics development.

Features:
- Closed-loop waypoint pursuit toward target slots broadcast by the Ground Station
- Local Artificial Potential Field (APF) obstacle & boundary avoidance
- Seamless manual teleoperation override via /cmd_vel
- Periodic telemetry transmission (Odometry at 20 Hz, Battery at 1 Hz, Sonar at 5 Hz)
"""

import math
import sys
import time
from typing import List, Tuple, Dict, Any

import rclpy
from usv_sdk import USVAgent, AutonomyMode, TargetPose, MarineObstacle


class USVAgentNode:
    """Autonomous marine agent control stack."""

    def __init__(self):
        # 1. Initialize underlying ROS 2 node context
        if not rclpy.ok():
            rclpy.init(args=sys.argv)

        # Temporary node to read parameters
        from rclpy.node import Node
        param_node = Node("usv_agent_param_loader")
        param_node.declare_parameter("usv_id", "usv_1")
        param_node.declare_parameter("initial_x", 0.0)
        param_node.declare_parameter("initial_y", 0.0)
        param_node.declare_parameter("initial_heading", 1.5707)  # North
        param_node.declare_parameter("max_speed", 4.2)           # m/s
        param_node.declare_parameter("cruise_speed", 2.8)        # m/s
        param_node.declare_parameter("publish_rate", 20.0)       # Hz

        self.usv_id = param_node.get_parameter("usv_id").get_parameter_value().string_value
        init_x = param_node.get_parameter("initial_x").get_parameter_value().double_value
        init_y = param_node.get_parameter("initial_y").get_parameter_value().double_value
        init_heading = param_node.get_parameter("initial_heading").get_parameter_value().double_value
        self.max_speed = param_node.get_parameter("max_speed").get_parameter_value().double_value
        self.cruise_speed = param_node.get_parameter("cruise_speed").get_parameter_value().double_value
        self.rate_hz = param_node.get_parameter("publish_rate").get_parameter_value().double_value
        param_node.destroy_node()

        # 2. Instantiate high-level SDK client
        self.agent = USVAgent(usv_id=self.usv_id, node_name=f"{self.usv_id}_autonomous_core")
        self.logger = self.agent.node.get_logger()
        self.logger.info(f"Starting USVAgentNode for '{self.usv_id}' at ({init_x:.1f}, {init_y:.1f})")

        # Kinematic state
        self.x = float(init_x)
        self.y = float(init_y)
        self.heading = float(init_heading)
        self.speed = 0.0
        self.yaw_rate = 0.0
        self.battery = 98.0
        self.voltage = 25.2

        # Waypoint & autonomy targets
        self.target_x = self.x
        self.target_y = self.y
        self.target_heading = self.heading
        self.mode = AutonomyMode.HOLD

        # Manual teleoperation inputs
        self.manual_linear_x = 0.0
        self.manual_angular_z = 0.0
        self.last_cmd_vel_time = 0.0

        # Environmental awareness (obstacles and geofence)
        self.known_obstacles: List[Dict[str, float]] = []
        self.active_geofence: List[Tuple[float, float]] = []

        # 3. Register SDK Event Callbacks
        self._register_callbacks()

        # 4. Timers for periodic loops
        dt = 1.0 / max(5.0, self.rate_hz)
        self.control_timer = self.agent.node.create_timer(dt, self._control_loop)
        self.battery_timer = self.agent.node.create_timer(1.0, self._battery_loop)
        self.sonar_timer = self.agent.node.create_timer(0.2, self._sonar_loop)

    def _register_callbacks(self):
        """Wire event callbacks with the USVAgent SDK."""

        @self.agent.on_target_pose
        def _on_target(target: TargetPose):
            self.logger.info(f"[{self.usv_id}] New target received: ({target.x:.1f}, {target.y:.1f})")
            self.target_x = target.x
            self.target_y = target.y
            self.target_heading = target.heading
            if self.mode != AutonomyMode.MANUAL:
                self.mode = AutonomyMode.FORMATION

        @self.agent.on_mode_change
        def _on_mode(mode: AutonomyMode):
            self.logger.info(f"[{self.usv_id}] Mode changed: {mode.value}")
            self.mode = mode
            if mode == AutonomyMode.HOLD:
                self.speed = 0.0
            elif mode == AutonomyMode.RTH:
                self.target_x = 0.0
                self.target_y = 0.0

        @self.agent.on_cmd_vel
        def _on_cmd_vel(linear_x: float, angular_z: float):
            self.manual_linear_x = linear_x
            self.manual_angular_z = angular_z
            self.last_cmd_vel_time = time.time()
            self.mode = AutonomyMode.MANUAL

        @self.agent.on_emergency_stop
        def _on_estop():
            self.logger.warn(f"[{self.usv_id}] EMERGENCY STOP ACTIVATED!")
            self.mode = AutonomyMode.HOLD
            self.speed = 0.0
            self.manual_linear_x = 0.0
            self.manual_angular_z = 0.0

        @self.agent.on_geofence_update
        def _on_geofence(points: List[Tuple[float, float]]):
            self.logger.info(f"[{self.usv_id}] Geofence updated with {len(points)} vertices")
            self.active_geofence = points

    def _control_loop(self):
        """High-rate kinematic control step (e.g. 20 Hz)."""
        dt = 1.0 / self.rate_hz

        # ── 1. Manual Drive Override ──
        if self.mode == AutonomyMode.MANUAL:
            # Failsafe: if no cmd_vel received in last 1.2s, coast down
            if time.time() - self.last_cmd_vel_time > 1.2:
                self.manual_linear_x = 0.0
                self.manual_angular_z = 0.0

            self.yaw_rate = self.manual_angular_z
            self.heading = (self.heading + self.yaw_rate * dt) % (2.0 * math.pi)

            # Throttle responsiveness
            if abs(self.manual_linear_x) > 0.01:
                self.speed += (self.manual_linear_x - self.speed) * 0.2
            else:
                self.speed *= 0.94  # Hydrodynamic coasting drag

        # ── 2. Autonomous Waypoint & APF Navigation ──
        elif self.mode in (AutonomyMode.FORMATION, AutonomyMode.TRANSIT, AutonomyMode.RTH, AutonomyMode.AVOIDING):
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist_to_target = math.hypot(dx, dy)

            # Attractive goal force vector
            if dist_to_target > 0.5:
                f_att_x = (dx / dist_to_target) * min(self.cruise_speed, dist_to_target * 0.7)
                f_att_y = (dy / dist_to_target) * min(self.cruise_speed, dist_to_target * 0.7)
            else:
                f_att_x, f_att_y = 0.0, 0.0

            # Repulsive obstacle force vector
            f_rep_x, f_rep_y = 0.0, 0.0
            danger_detected = False

            for obs in self.known_obstacles:
                odx = self.x - obs['x']
                ody = self.y - obs['y']
                odist = math.hypot(odx, ody)
                r_safe = obs.get('radius', 5.0) + 4.0
                if odist < r_safe and odist > 0.05:
                    danger_detected = True
                    rep_mag = 4.5 * ((1.0 / odist) - (1.0 / r_safe)) / (odist * odist)
                    rep_mag = min(6.0, rep_mag)
                    f_rep_x += (odx / odist) * rep_mag
                    f_rep_y += (ody / odist) * rep_mag

            # Repulsive geofence boundary force
            if len(self.active_geofence) >= 3:
                for i in range(len(self.active_geofence)):
                    p1 = self.active_geofence[i]
                    p2 = self.active_geofence[(i + 1) % len(self.active_geofence)]
                    # Distance to line segment
                    seg_dx = p2[0] - p1[0]
                    seg_dy = p2[1] - p1[1]
                    seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy
                    if seg_len_sq > 0.001:
                        t = max(0.0, min(1.0, ((self.x - p1[0]) * seg_dx + (self.y - p1[1]) * seg_dy) / seg_len_sq))
                        near_x = p1[0] + t * seg_dx
                        near_y = p1[1] + t * seg_dy
                        b_dist = math.hypot(self.x - near_x, self.y - near_y)
                        if b_dist < 6.0 and b_dist > 0.05:
                            danger_detected = True
                            b_rep = 5.0 * ((1.0 / b_dist) - (1.0 / 6.0))
                            f_rep_x += ((self.x - near_x) / b_dist) * b_rep
                            f_rep_y += ((self.y - near_y) / b_dist) * b_rep

            # Resultant guidance vector
            res_vx = f_att_x + f_rep_x
            res_vy = f_att_y + f_rep_y
            res_speed = math.hypot(res_vx, res_vy)

            if res_speed > 0.1:
                desired_heading = math.atan2(res_vy, res_vx)
                err = (desired_heading - self.heading + math.pi) % (2.0 * math.pi) - math.pi
                turn_rate = max(-2.0, min(2.0, err * 2.5))
                self.yaw_rate = turn_rate
                self.heading = (self.heading + turn_rate * dt) % (2.0 * math.pi)

                target_speed = min(self.max_speed, res_speed)
                if abs(err) > 0.8:
                    target_speed *= 0.4  # Slow down in sharp turns
                self.speed += (target_speed - self.speed) * 0.15
            else:
                self.speed *= 0.85
                self.yaw_rate = 0.0

        elif self.mode == AutonomyMode.HOLD:
            self.speed *= 0.85
            self.yaw_rate = 0.0

        # Integrate forward displacement
        self.x += math.cos(self.heading) * self.speed * dt
        self.y += math.sin(self.heading) * self.speed * dt

        # Publish state over ROS 2 Odometry
        self.agent.publish_odom(
            x=self.x,
            y=self.y,
            heading=self.heading,
            speed=self.speed,
            yaw_rate=self.yaw_rate
        )

    def _battery_loop(self):
        """Low-rate battery health update (1 Hz)."""
        discharge_rate = 0.003 if abs(self.speed) > 0.5 else 0.0008
        self.battery = max(3.0, self.battery - discharge_rate)
        self.voltage = 22.0 + (self.battery / 100.0) * 3.4
        self.agent.publish_battery(soc_pct=self.battery, voltage=self.voltage)

    def _sonar_loop(self):
        """Sonar soundings and forward depth telemetry (5 Hz)."""
        sim_depth = 16.5 + 4.0 * math.sin(self.x * 0.015) + 3.0 * math.cos(self.y * 0.015)
        self.agent.publish_sonar(range_m=sim_depth)

    def spin(self):
        """Block until user interruption."""
        try:
            self.agent.spin()
        except KeyboardInterrupt:
            pass
        finally:
            self.agent.shutdown()


def main():
    agent_node = USVAgentNode()
    agent_node.spin()


if __name__ == "__main__":
    main()
