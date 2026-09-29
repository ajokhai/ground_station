"""
USV Ground Station Node with integrated PyQt5 GUI.
Coordinates USV swarm formations, telemetry monitoring, and mission dispatch.
"""

import sys
import json
import math
import signal
from typing import Dict, Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist, PolygonStamped, Point32, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState, Range, CompressedImage
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from ground_station.gui.main_window import MainWindow


class GroundStationNode(Node):
    def __init__(self):
        super().__init__('ground_station_node')
        self.get_logger().info('Ground Station ROS 2 Node initialized.')

        # Multi-agent dynamic downlink publishers pool
        self.target_pose_pubs: Dict[str, Any] = {}
        self.autonomy_mode_pubs: Dict[str, Any] = {}
        self.cmd_vel_pubs: Dict[str, Any] = {}

        # Multi-agent dynamic uplink subscribers pool
        self.odom_subs: Dict[str, Any] = {}
        self.battery_subs: Dict[str, Any] = {}
        self.sonar_subs: Dict[str, Any] = {}
        self.camera_subs: Dict[str, Any] = {}

        # Inbound telemetry callbacks for GUI dispatch
        self.odom_callback = None
        self.battery_callback = None
        self.sonar_callback = None
        self.camera_callback = None
        self.usv_discovered_callback = None


        # Publishers
        self.formation_pub = self.create_publisher(
            String,
            '/ground_station/formation_cmd',
            10
        )
        self.estop_pub = self.create_publisher(
            Bool,
            '/ground_station/emergency_stop',
            10
        )
        self.heartbeat_pub = self.create_publisher(
            String,
            '/ground_station/heartbeat',
            10
        )

        geofence_qos = QoSProfile(
            depth=10,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )
        self.geofence_pub = self.create_publisher(
            PolygonStamped,
            '/ground_station/geofence',
            geofence_qos
        )


        # Subscribers
        self.obstacle_sub = self.create_subscription(
            String,
            '/ground_station/detected_obstacles',
            self._on_obstacles_received,
            10
        )
        self.obstacle_callback = None

        # Heartbeat timer (1 Hz)
        self.heartbeat_timer = self.create_timer(1.0, self._publish_heartbeat)
        self.heartbeat_counter = 0

        # Dynamic USV auto-discovery timer (1.5 Hz)
        self.discovery_timer = self.create_timer(1.5, self._discover_usvs)

    def _on_obstacles_received(self, msg: String):
        try:
            data = json.loads(msg.data)
            if self.obstacle_callback:
                self.obstacle_callback(data)
        except Exception as e:
            self.get_logger().warn(f"Failed to parse obstacle message: {e}")

    def _publish_heartbeat(self):
        self.heartbeat_counter += 1
        msg = String()
        msg.data = json.dumps({
            'source': 'ground_station',
            'seq': self.heartbeat_counter,
            'status': 'OPERATIONAL'
        })
        self.heartbeat_pub.publish(msg)

    def publish_formation_command(self, cmd_dict):
        msg = String()
        msg.data = json.dumps(cmd_dict)
        self.formation_pub.publish(msg)
        self.get_logger().info(f"Published Formation Command: {cmd_dict.get('action')} - {cmd_dict.get('formation', '')}")

    def publish_emergency_stop(self, stop_state=True):
        msg = Bool()
        msg.data = stop_state
        self.estop_pub.publish(msg)
        self.get_logger().warn("Published EMERGENCY STOP command!")

    def publish_geofence(self, gf_dict: dict):
        """
        Broadcast geofence polygon to all USVs and external simulators via ROS 2.
        Topic: /ground_station/geofence
        Type: geometry_msgs/msg/PolygonStamped
        """
        try:
            msg = PolygonStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            name = str(gf_dict.get('name', 'ZONE'))
            msg.header.frame_id = f"map:{name}"

            pts = []
            for pt in gf_dict.get('points', []):
                p32 = Point32()
                p32.x = float(pt[0])
                p32.y = float(pt[1])
                p32.z = 0.0
                pts.append(p32)
            msg.polygon.points = pts

            self.geofence_pub.publish(msg)
            self.get_logger().info(
                f"Broadcast Geofence '{name}' ({len(pts)} vertices) to /ground_station/geofence"
            )
        except Exception as e:
            self.get_logger().error(f"Failed to publish geofence: {e}")

    def _normalize_usv_ns(self, usv_id: str) -> str:
        """Normalize 'USV-1', 'usv-1', or '1' to valid ROS 2 topic namespace 'usv_1'."""
        clean = usv_id.lower().replace('-', '_').strip()
        if not clean.startswith('usv'):
            clean = f"usv_{clean}"
        return clean

    def _ns_to_usv_id(self, ns: str) -> str:
        """Convert ROS 2 topic namespace 'usv_1' back to UI identifier 'USV-1'."""
        parts = ns.split('_')
        if len(parts) >= 2 and parts[0].lower() == 'usv':
            return f"USV-{parts[1].upper()}"
        return ns.upper()

    def _get_or_create_usv_publishers(self, usv_id: str):
        ns = self._normalize_usv_ns(usv_id)
        if ns not in self.target_pose_pubs:
            topic_pose = f"/{ns}/target_pose"
            topic_mode = f"/{ns}/autonomy_mode"
            topic_cmd = f"/{ns}/cmd_vel"
            self.target_pose_pubs[ns] = self.create_publisher(PoseStamped, topic_pose, 10)
            self.autonomy_mode_pubs[ns] = self.create_publisher(String, topic_mode, 10)
            self.cmd_vel_pubs[ns] = self.create_publisher(Twist, topic_cmd, 10)
            self.get_logger().info(f"Initialized downlink publishers for {usv_id}: {topic_pose}, {topic_mode}, {topic_cmd}")
        return self.target_pose_pubs[ns], self.autonomy_mode_pubs[ns]

    def publish_usv_target_pose(self, usv_id: str, x: float, y: float, heading_rad: float = 0.0):
        """
        Downlink: /usv_{id}/target_pose (geometry_msgs/PoseStamped)
        Publishes assigned target slot coordinates or individual waypoint for a specific USV.
        """
        try:
            pose_pub, _ = self._get_or_create_usv_publishers(usv_id)
            msg = PoseStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'map'
            msg.pose.position.x = float(x)
            msg.pose.position.y = float(y)
            msg.pose.position.z = 0.0
            msg.pose.orientation.x = 0.0
            msg.pose.orientation.y = 0.0
            msg.pose.orientation.z = math.sin(heading_rad / 2.0)
            msg.pose.orientation.w = math.cos(heading_rad / 2.0)
            pose_pub.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Failed to publish target_pose for {usv_id}: {e}")

    def publish_usv_autonomy_mode(self, usv_id: str, mode: str):
        """
        Downlink: /usv_{id}/autonomy_mode (std_msgs/String)
        Publishes autonomy directive: FORMATION, TRANSIT, HOLD, RTH, MANUAL, AVOIDING.
        """
        try:
            _, mode_pub = self._get_or_create_usv_publishers(usv_id)
            msg = String()
            msg.data = mode.upper()
            mode_pub.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Failed to publish autonomy_mode for {usv_id}: {e}")

    def publish_usv_cmd_vel(self, usv_id: str, linear_x: float, angular_z: float):
        """
        Downlink: /usv_{id}/cmd_vel (geometry_msgs/Twist)
        Publishes manual velocity override when operator drives a vehicle via keyboard or joystick.
        """
        try:
            ns = self._normalize_usv_ns(usv_id)
            if ns not in self.cmd_vel_pubs:
                self._get_or_create_usv_publishers(usv_id)
            msg = Twist()
            msg.linear.x = float(linear_x)
            msg.linear.y = 0.0
            msg.linear.z = 0.0
            msg.angular.x = 0.0
            msg.angular.y = 0.0
            msg.angular.z = float(angular_z)
            self.cmd_vel_pubs[ns].publish(msg)
        except Exception as e:
            self.get_logger().error(f"Failed to publish cmd_vel for {usv_id}: {e}")

    # ── Inbound Telemetry Subscriptions (Uplink Bridge) ──

    def ensure_usv_subscribers(self, usv_id: str):
        """Ensure multi-topic subscriber pool exists for a given USV."""
        ns = self._normalize_usv_ns(usv_id)
        if ns in self.odom_subs:
            return

        topic_odom = f"/{ns}/odom"
        topic_bat = f"/{ns}/battery"
        topic_sonar = f"/{ns}/sensors/sonar"
        topic_cam = f"/{ns}/camera/image_raw/compressed"

        self.odom_subs[ns] = self.create_subscription(
            Odometry,
            topic_odom,
            lambda msg, uid=usv_id: self._on_usv_odom_received(msg, uid),
            10
        )
        self.battery_subs[ns] = self.create_subscription(
            BatteryState,
            topic_bat,
            lambda msg, uid=usv_id: self._on_usv_battery_received(msg, uid),
            10
        )
        self.sonar_subs[ns] = self.create_subscription(
            Range,
            topic_sonar,
            lambda msg, uid=usv_id: self._on_usv_sonar_received(msg, uid),
            10
        )
        self.camera_subs[ns] = self.create_subscription(
            CompressedImage,
            topic_cam,
            lambda msg, uid=usv_id: self._on_usv_camera_received(msg, uid),
            10
        )
        self.get_logger().info(f"Subscribed to live telemetry topics for {usv_id} ({ns})")

    def _on_usv_odom_received(self, msg: Odometry, usv_id: str):
        try:
            x = float(msg.pose.pose.position.x)
            y = float(msg.pose.pose.position.y)
            qx = float(msg.pose.pose.orientation.x)
            qy = float(msg.pose.pose.orientation.y)
            qz = float(msg.pose.pose.orientation.z)
            qw = float(msg.pose.pose.orientation.w)
            heading = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
            heading = (heading + 2.0 * math.pi) % (2.0 * math.pi)
            speed = math.hypot(float(msg.twist.twist.linear.x), float(msg.twist.twist.linear.y))

            if self.odom_callback:
                self.odom_callback(usv_id, x, y, heading, speed)
        except Exception as e:
            self.get_logger().warn(f"Failed to process odom for {usv_id}: {e}")

    def _on_usv_battery_received(self, msg: BatteryState, usv_id: str):
        try:
            pct = float(msg.percentage)
            if pct <= 1.0:
                pct *= 100.0
            pct = max(0.0, min(100.0, pct))
            voltage = float(msg.voltage) if hasattr(msg, 'voltage') else 0.0
            if self.battery_callback:
                self.battery_callback(usv_id, pct, voltage)
        except Exception as e:
            self.get_logger().warn(f"Failed to process battery for {usv_id}: {e}")

    def _on_usv_sonar_received(self, msg: Range, usv_id: str):
        try:
            rng = float(msg.range)
            if self.sonar_callback:
                self.sonar_callback(usv_id, rng)
        except Exception as e:
            self.get_logger().warn(f"Failed to process sonar for {usv_id}: {e}")

    def _on_usv_camera_received(self, msg: CompressedImage, usv_id: str):
        try:
            data = bytes(msg.data)
            if self.camera_callback:
                self.camera_callback(usv_id, data)
        except Exception as e:
            self.get_logger().warn(f"Failed to process camera for {usv_id}: {e}")

    def _discover_usvs(self):
        """Periodically scan ROS 2 topic graph for active USVs and bind subscribers."""
        try:
            topic_names_and_types = self.get_topic_names_and_types()
            for topic_name, _ in topic_names_and_types:
                parts = topic_name.strip('/').split('/')
                if len(parts) >= 2 and parts[0].startswith('usv_'):
                    ns = parts[0]
                    usv_id = self._ns_to_usv_id(ns)
                    if ns not in self.odom_subs:
                        self.ensure_usv_subscribers(usv_id)
                        if self.usv_discovered_callback:
                            self.usv_discovered_callback(usv_id)
        except Exception:
            pass


def main(args=None):
    # Initialize ROS 2
    rclpy.init(args=args)
    ros_node = GroundStationNode()

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("USV Ground Station")

    # Create Main Window
    window = MainWindow(ros_node=ros_node)

    # Connect Window Signals to ROS 2 Node Publishers
    window.formation_command_signal.connect(ros_node.publish_formation_command)
    window.emergency_stop_signal.connect(ros_node.publish_emergency_stop)
    window.geofence_broadcast_signal.connect(ros_node.publish_geofence)
    window.usv_target_pose_signal.connect(ros_node.publish_usv_target_pose)
    window.usv_autonomy_mode_signal.connect(ros_node.publish_usv_autonomy_mode)
    window.usv_cmd_vel_signal.connect(ros_node.publish_usv_cmd_vel)
    ros_node.obstacle_callback = window.ingest_external_obstacle
    ros_node.odom_callback = window.ingest_external_usv_odom
    ros_node.battery_callback = window.ingest_external_usv_battery
    ros_node.sonar_callback = window.ingest_external_usv_sonar
    ros_node.camera_callback = window.ingest_external_usv_camera
    ros_node.usv_discovered_callback = window.register_external_usv

    # Pre-subscribe to all existing fleet members
    for uid in window.usv_fleet.keys():
        ros_node.ensure_usv_subscribers(uid)



    # Safe ROS 2 event loop via QTimer
    is_shutting_down = False

    def _safe_ros_spin():
        nonlocal is_shutting_down
        if not is_shutting_down and rclpy.ok():
            try:
                rclpy.spin_once(ros_node, timeout_sec=0)
            except Exception:
                pass

    ros_spin_timer = QTimer()
    ros_spin_timer.timeout.connect(_safe_ros_spin)
    ros_spin_timer.start(20)  # Spin at 50 Hz

    def sigint_handler(sig, frame):
        nonlocal is_shutting_down
        is_shutting_down = True
        ros_spin_timer.stop()
        app.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Center window on screen
    screen_geom = app.primaryScreen().availableGeometry()
    win_geom = window.frameGeometry()
    win_geom.moveCenter(screen_geom.center())
    window.move(win_geom.topLeft())

    window.show()
    window.raise_()
    window.activateWindow()

    # On macOS, force window to front of other applications
    if sys.platform == 'darwin':
        try:
            import os, subprocess
            pid = os.getpid()
            subprocess.run([
                'osascript', '-e',
                f'tell application "System Events" to set frontmost of first process whose unix id is {pid} to true'
            ], capture_output=True, check=False)
        except Exception:
            pass

    # Run Qt Event Loop
    exit_code = app.exec_()

    # Clean shutdown
    is_shutting_down = True
    ros_spin_timer.stop()
    if rclpy.ok():
        try:
            ros_node.destroy_node()
        except Exception:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass
    sys.exit(exit_code)


if __name__ == '__main__':
    main()