"""
HERMORD USV Ground Station Node with integrated PyQt5 GUI.
Coordinates USV swarm formations, telemetry monitoring, and mission dispatch.
"""

import sys
import json
import signal
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from ground_station.gui.main_window import MainWindow


class GroundStationNode(Node):
    def __init__(self):
        super().__init__('ground_station_node')
        self.get_logger().info('Ground Station ROS 2 Node initialized.')

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

        # Heartbeat timer (1 Hz)
        self.heartbeat_timer = self.create_timer(1.0, self._publish_heartbeat)
        self.heartbeat_counter = 0

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


def main(args=None):
    # Allow clean Ctrl+C termination from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Initialize ROS 2
    rclpy.init(args=args)
    ros_node = GroundStationNode()

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("HERMORD Ground Station")

    # Create Main Window
    window = MainWindow(ros_node=ros_node)

    # Connect Window Signals to ROS 2 Node Publishers
    window.formation_command_signal.connect(ros_node.publish_formation_command)
    window.emergency_stop_signal.connect(ros_node.publish_emergency_stop)

    # Integrate ROS 2 event loop with Qt event loop via QTimer
    def _safe_ros_spin():
        if rclpy.ok():
            try:
                rclpy.spin_once(ros_node, timeout_sec=0)
            except Exception:
                pass

    ros_spin_timer = QTimer()
    ros_spin_timer.timeout.connect(_safe_ros_spin)
    ros_spin_timer.start(20)  # Spin at 50 Hz

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
    ros_node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()