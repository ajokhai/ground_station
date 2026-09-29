# USV Fleet Python SDK (`usv_sdk`)

The **USV Fleet Python SDK** is a lightweight, zero-boilerplate ROS 2 client library for connecting physical autonomous surface vessels (NVIDIA Jetson, Raspberry Pi, x86 marine computers) and simulation environments (NVIDIA Isaac Sim, Gazebo, MuJoCo, MATLAB/Simulink) to the **USV Ground Station**.

---

## Key Features

- **Decorator Event Callbacks**: Clean Python decorators (`@agent.on_target_pose`, `@agent.on_mode_change`, `@agent.on_cmd_vel`, `@agent.on_emergency_stop`, `@agent.on_geofence_update`).
- **Standardized ROS 2 Message Dispatch**: Simple one-line telemetry publishers for `nav_msgs/Odometry`, `sensor_msgs/BatteryState`, `sensor_msgs/Range`, and `sensor_msgs/CompressedImage`.
- **Dynamic Auto-Discovery Compatible**: Fully adheres to `/usv_{id}/*` topic schemas detected automatically by the Ground Station's 1.5 Hz discovery daemon.
- **Swarm Test Harness CLI**: Instant multi-agent swarm generator (`python -m usv_sdk.cli swarm --count 4`) for load and formation testing.

---

## Installation & Environment

The SDK requires Python 3.10+ and a standard ROS 2 Humble desktop environment.

From within your repository or workspace:

```bash
# Sourcing ROS 2 environment
source /opt/ros/humble/setup.bash  # Linux
# or inside pixi
pixi shell
```

---

## Quickstart: Onboarding a USV in 10 Lines of Python

```python
from usv_sdk import USVAgent, TargetPose, AutonomyMode

# Initialize agent for vehicle namespace "usv_1"
agent = USVAgent(usv_id="usv_1")

# Register waypoint target handler
@agent.on_target_pose
def handle_target(target: TargetPose):
    print(f"Received new target slot from Ground Station: ({target.x:.1f}, {target.y:.1f})")

# Register teleoperation drive handler
@agent.on_cmd_vel
def handle_manual_drive(linear_x: float, angular_z: float):
    print(f"Manual teleop command: surge={linear_x:.2f} m/s, turn={angular_z:.2f} rad/s")

# Start background ROS 2 event loop
agent.start_async()

# Dispatch periodic telemetry (e.g. at 20 Hz in your control loop)
agent.publish_odom(x=12.5, y=45.2, heading=1.57, speed=3.2)
agent.publish_battery(soc_pct=94.5, voltage=25.2)
agent.publish_sonar(range_m=14.8)
```

---

## Swarm Test Harness CLI

You can spin up mock vessels or full swarms directly from the command line without any physical hardware:

### 1. Launch a Single Mock USV
```bash
python -m usv_sdk.cli mock --id usv_1 --start-x 10.0 --start-y 20.0
```

### 2. Launch an Autonomous 4-Vehicle Swarm
```bash
python -m usv_sdk.cli swarm --count 4 --spacing 20.0
```

Switch the Ground Station toolbar mode to **`📡 External ROS 2 / Hardware`** to observe the mock swarm instantly appear on the tactical radar and respond to formation geometry changes!

---

## Standard Topic Schema

| Direction | Topic | ROS 2 Message Type | SDK Helper Method / Callback |
| :--- | :--- | :--- | :--- |
| **Uplink** | `/{ns}/odom` | `nav_msgs/msg/Odometry` | `agent.publish_odom()` |
| **Uplink** | `/{ns}/battery` | `sensor_msgs/msg/BatteryState` | `agent.publish_battery()` |
| **Uplink** | `/{ns}/sensors/sonar` | `sensor_msgs/msg/Range` | `agent.publish_sonar()` |
| **Uplink** | `/{ns}/camera/image_raw/compressed` | `sensor_msgs/msg/CompressedImage` | `agent.publish_camera_frame()` |
| **Uplink** | `/ground_station/detected_obstacles` | `visualization_msgs/msg/MarkerArray` | `agent.publish_obstacle()` |
| **Downlink** | `/{ns}/target_pose` | `geometry_msgs/msg/PoseStamped` | `@agent.on_target_pose` |
| **Downlink** | `/{ns}/autonomy_mode` | `std_msgs/msg/String` | `@agent.on_mode_change` |
| **Downlink** | `/{ns}/cmd_vel` | `geometry_msgs/msg/Twist` | `@agent.on_cmd_vel` |
| **Downlink** | `/ground_station/emergency_stop` | `std_msgs/msg/Bool` | `@agent.on_emergency_stop` |
| **Downlink** | `/ground_station/geofence` | `geometry_msgs/msg/PolygonStamped` | `@agent.on_geofence_update` |
