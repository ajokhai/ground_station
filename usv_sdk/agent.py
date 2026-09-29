"""
USVAgent — Core client interface for vehicle and simulator onboarding.
"""

import json
import logging
import math
import sys
import threading
import time
from typing import Callable, List, Optional, Tuple, Union

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
    from geometry_msgs.msg import PoseStamped, Twist, PolygonStamped, Point32
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import BatteryState, Range, CompressedImage
    from std_msgs.msg import String, Bool
    from visualization_msgs.msg import Marker, MarkerArray
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

from .models import AutonomyMode, TelemetryState, TargetPose, MarineObstacle, quaternion_to_yaw

logger = logging.getLogger("usv_sdk")


class USVAgent:
    """
    USVAgent provides a high-level, zero-boilerplate Python client library
    for connecting autonomous surface craft, companion computers, and simulation
    runtimes to the USV Ground Station.

    Usage:
        >>> from usv_sdk import USVAgent
        >>> agent = USVAgent(usv_id="usv_1")
        >>> 
        >>> @agent.on_target_pose
        >>> def handle_target(target: TargetPose):
        ...     print(f"New waypoint: x={target.x}, y={target.y}")
        >>> 
        >>> agent.start_async()
        >>> agent.publish_odom(x=10.0, y=25.0, heading=1.57, speed=2.5)
    """

    def __init__(self, usv_id: Union[str, int], node_name: Optional[str] = None):
        if not ROS2_AVAILABLE:
            raise RuntimeError(
                "ROS 2 (rclpy) is not installed or sourced in the current Python environment. "
                "Ensure your environment has ros-humble-desktop active."
            )

        # Normalize USV identifier: e.g. "USV-1" -> "usv_1", 2 -> "usv_2"
        raw_id = str(usv_id).strip().lower().replace("-", "_")
        if not raw_id.startswith("usv_"):
            raw_id = f"usv_{raw_id}"
        self.usv_id = raw_id

        # Internal state
        self.current_state = TelemetryState()
        self.current_mode = AutonomyMode.HOLD
        self.latest_target: Optional[TargetPose] = None
        self.active_geofence: List[Tuple[float, float]] = []

        # Registered user event callbacks
        self._target_pose_cb: Optional[Callable[[TargetPose], None]] = None
        self._mode_change_cb: Optional[Callable[[AutonomyMode], None]] = None
        self._cmd_vel_cb: Optional[Callable[[float, float], None]] = None
        self._estop_cb: Optional[Callable[[], None]] = None
        self._geofence_cb: Optional[Callable[[List[Tuple[float, float]]], None]] = None

        # Threading control
        self._spin_thread: Optional[threading.Thread] = None
        self._running = False

        # Initialize ROS 2 context if needed
        if not rclpy.ok():
            rclpy.init(args=sys.argv)

        actual_node_name = node_name or f"{self.usv_id}_agent_client"
        self.node = Node(actual_node_name)

        # Configure QoS profiles
        self._setup_publishers_and_subscribers()
        logger.info(f"USVAgent initialized for vehicle namespace: {self.usv_id}")

    def _setup_publishers_and_subscribers(self):
        """Bind ROS 2 uplink publishers and downlink subscribers."""
        ns = self.usv_id

        # Standard transient local QoS for geofence and formation setup
        qos_transient = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ── Uplink Publishers (Vehicle/Sim -> Ground Station) ──
        self._pub_odom = self.node.create_publisher(Odometry, f"/{ns}/odom", 10)
        self._pub_battery = self.node.create_publisher(BatteryState, f"/{ns}/battery", 10)
        self._pub_sonar = self.node.create_publisher(Range, f"/{ns}/sensors/sonar", 10)
        self._pub_camera = self.node.create_publisher(CompressedImage, f"/{ns}/camera/image_raw/compressed", 10)
        self._pub_obstacles = self.node.create_publisher(MarkerArray, "/ground_station/detected_obstacles", 10)

        # ── Downlink Subscribers (Ground Station -> Vehicle) ──
        self._sub_target_pose = self.node.create_subscription(
            PoseStamped,
            f"/{ns}/target_pose",
            self._handle_target_pose_msg,
            10
        )
        self._sub_autonomy_mode = self.node.create_subscription(
            String,
            f"/{ns}/autonomy_mode",
            self._handle_autonomy_mode_msg,
            10
        )
        self._sub_cmd_vel = self.node.create_subscription(
            Twist,
            f"/{ns}/cmd_vel",
            self._handle_cmd_vel_msg,
            10
        )
        self._sub_estop = self.node.create_subscription(
            Bool,
            "/ground_station/emergency_stop",
            self._handle_estop_msg,
            10
        )
        self._sub_geofence = self.node.create_subscription(
            PolygonStamped,
            "/ground_station/geofence",
            self._handle_geofence_msg,
            qos_transient
        )

    # ── Incoming Message Handlers ──

    def _handle_target_pose_msg(self, msg: PoseStamped):
        x = msg.pose.position.x
        y = msg.pose.position.y
        q = msg.pose.orientation
        yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w)
        target = TargetPose(x=x, y=y, heading=yaw, frame_id=msg.header.frame_id)
        self.latest_target = target
        if self._target_pose_cb:
            try:
                self._target_pose_cb(target)
            except Exception as e:
                logger.error(f"Error in on_target_pose callback: {e}")

    def _handle_autonomy_mode_msg(self, msg: String):
        try:
            mode = AutonomyMode(msg.data.strip().upper())
        except ValueError:
            mode = AutonomyMode.HOLD
        self.current_mode = mode
        if self._mode_change_cb:
            try:
                self._mode_change_cb(mode)
            except Exception as e:
                logger.error(f"Error in on_mode_change callback: {e}")

    def _handle_cmd_vel_msg(self, msg: Twist):
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        if self._cmd_vel_cb:
            try:
                self._cmd_vel_cb(linear_x, angular_z)
            except Exception as e:
                logger.error(f"Error in on_cmd_vel callback: {e}")

    def _handle_estop_msg(self, msg: Bool):
        if msg.data:
            self.current_mode = AutonomyMode.HOLD
            if self._estop_cb:
                try:
                    self._estop_cb()
                except Exception as e:
                    logger.error(f"Error in on_emergency_stop callback: {e}")

    def _handle_geofence_msg(self, msg: PolygonStamped):
        points = [(p.x, p.y) for p in msg.polygon.points]
        self.active_geofence = points
        if self._geofence_cb:
            try:
                self._geofence_cb(points)
            except Exception as e:
                logger.error(f"Error in on_geofence_update callback: {e}")

    # ── Decorator Callback Registration ──

    def on_target_pose(self, func: Callable[[TargetPose], None]):
        """Register callback for target waypoint / slot updates from Ground Station."""
        self._target_pose_cb = func
        return func

    def on_mode_change(self, func: Callable[[AutonomyMode], None]):
        """Register callback for autonomy mode transitions (FORMATION, HOLD, etc.)."""
        self._mode_change_cb = func
        return func

    def on_cmd_vel(self, func: Callable[[float, float], None]):
        """Register callback for manual teleoperation (linear_x, angular_z)."""
        self._cmd_vel_cb = func
        return func

    def on_emergency_stop(self, func: Callable[[], None]):
        """Register callback for emergency stop triggers."""
        self._estop_cb = func
        return func

    def on_geofence_update(self, func: Callable[[List[Tuple[float, float]]], None]):
        """Register callback for keep-out boundary polygon updates."""
        self._geofence_cb = func
        return func

    # ── Telemetry Dispatchers (Publishing to Ground Station) ──

    def publish_odom(
        self,
        x: float,
        y: float,
        heading: float,
        speed: float = 0.0,
        yaw_rate: float = 0.0,
        z: float = 0.0,
        sway_speed: float = 0.0
    ):
        """
        Publish kinematic odometry state to /{usv_id}/odom.

        Args:
            x: Local Easting in meters (ENU)
            y: Local Northing in meters (ENU)
            heading: Planar yaw angle in radians
            speed: Forward surge speed in m/s
            yaw_rate: Yaw rotational speed in rad/s
            z: Altitude/depth in meters
            sway_speed: Lateral sway speed in m/s
        """
        self.current_state.x = float(x)
        self.current_state.y = float(y)
        self.current_state.z = float(z)
        self.current_state.heading = float(heading)
        self.current_state.speed = float(speed)
        self.current_state.sway_speed = float(sway_speed)
        self.current_state.yaw_rate = float(yaw_rate)
        self.current_state.timestamp = time.time()

        msg = Odometry()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = "world"
        msg.child_frame_id = f"{self.usv_id}_base_link"

        # Position
        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)
        msg.pose.pose.position.z = float(z)

        # Orientation
        qx, qy, qz, qw = self.current_state.to_quaternion()
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        # Velocity
        msg.twist.twist.linear.x = float(speed)
        msg.twist.twist.linear.y = float(sway_speed)
        msg.twist.twist.angular.z = float(yaw_rate)

        self._pub_odom.publish(msg)

    def publish_battery(self, soc_pct: float, voltage: float = 24.0):
        """
        Publish battery telemetry to /{usv_id}/battery.

        Args:
            soc_pct: State of charge percentage (0.0 to 100.0)
            voltage: Bus voltage in Volts (e.g. 24.0)
        """
        self.current_state.battery_pct = float(soc_pct)
        self.current_state.voltage = float(voltage)

        msg = BatteryState()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.percentage = float(max(0.0, min(100.0, soc_pct))) / 100.0  # standard ROS 2 is 0.0 - 1.0
        msg.voltage = float(voltage)
        self._pub_battery.publish(msg)

    def publish_sonar(self, range_m: float, min_range: float = 0.2, max_range: float = 40.0):
        """
        Publish acoustic sounding / forward distance to /{usv_id}/sensors/sonar.

        Args:
            range_m: Measured obstacle or bottom sounding in meters
            min_range: Minimum reliable transducer distance
            max_range: Maximum transducer range
        """
        self.current_state.sonar_depth_m = float(range_m)

        msg = Range()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = f"{self.usv_id}_sonar_link"
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.52  # ~30 deg cone
        msg.min_range = float(min_range)
        msg.max_range = float(max_range)
        msg.range = float(range_m)
        self._pub_sonar.publish(msg)

    def publish_camera_frame(self, jpeg_bytes: bytes, frame_id: Optional[str] = None):
        """
        Publish a JPEG compressed camera frame to /{usv_id}/camera/image_raw/compressed.

        Args:
            jpeg_bytes: Binary encoded JPEG image data
            frame_id: Optical frame identifier
        """
        msg = CompressedImage()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = frame_id or f"{self.usv_id}_optical_frame"
        msg.format = "jpeg"
        msg.data = list(jpeg_bytes)
        self._pub_camera.publish(msg)

    def publish_obstacle(self, x: float, y: float, radius: float = 5.0, label: str = "HAZARD", obs_id: int = 1):
        """
        Publish a detected marine hazard to /ground_station/detected_obstacles.
        """
        marker = Marker()
        marker.header.stamp = self.node.get_clock().now().to_msg()
        marker.header.frame_id = "world"
        marker.ns = f"{self.usv_id}_hazards"
        marker.id = int(obs_id)
        marker.type = Marker.CYLINDER
        marker.action = Marker.ADD
        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y)
        marker.pose.position.z = 0.0
        marker.pose.orientation.w = 1.0
        marker.scale.x = float(radius * 2.0)
        marker.scale.y = float(radius * 2.0)
        marker.scale.z = 2.0
        marker.color.r = 1.0
        marker.color.g = 0.65
        marker.color.b = 0.0
        marker.color.a = 0.8
        marker.text = str(label)

        array = MarkerArray()
        array.markers.append(marker)
        self._pub_obstacles.publish(array)

    # ── Lifecycle & Spinning Control ──

    def spin_once(self, timeout_sec: float = 0.02):
        """Execute a single ROS 2 spin cycle."""
        rclpy.spin_once(self.node, timeout_sec=timeout_sec)

    def spin(self):
        """Blockingly spin the agent node until interrupted."""
        try:
            rclpy.spin(self.node)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def start_async(self) -> threading.Thread:
        """
        Start spinning the agent in a background daemon thread.
        Returns the started thread.
        """
        if self._running:
            return self._spin_thread

        self._running = True

        def _loop():
            while self._running and rclpy.ok():
                try:
                    rclpy.spin_once(self.node, timeout_sec=0.05)
                except Exception as e:
                    if self._running:
                        logger.error(f"Error in spin_once loop: {e}")
                    break

        self._spin_thread = threading.Thread(target=_loop, daemon=True, name=f"{self.usv_id}_spin_thread")
        self._spin_thread.start()
        return self._spin_thread

    def shutdown(self):
        """Gracefully terminate agent publishers, subscribers, and background threads."""
        self._running = False
        if self._spin_thread and self._spin_thread.is_alive():
            self._spin_thread.join(timeout=1.0)
        try:
            self.node.destroy_node()
        except Exception:
            pass
        logger.info(f"USVAgent {self.usv_id} shut down gracefully.")
