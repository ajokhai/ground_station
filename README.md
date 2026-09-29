# USV Ground Station

A ROS 2 Humble ground station package for managing, coordinating, and monitoring Unmanned Surface Vehicle (USV) swarm formations.

## Features

- **Tactical 2D Radar & Map Display**:
  - Live USV vessel glyphs with real-time headings and trajectory trails
  - Concentric range rings (meters) and radar sweep animation
  - Interactive target formation geometry overlay (ghost markers and connecting formation lines)
  - Zoom (wheel / buttons) and Pan (middle-click or shift-drag)
  - Dynamic scale bar (Meters and Nautical Miles) and cursor GPS readout
- **Georeferencing & Environmental Map Layers**:
  - WGS84 $\leftrightarrow$ local ENU projection engine with configurable Datum anchor
  - Tile switcher: **Grid**, **Tactical**, **Satellite** (ESRI World Imagery), **Nautical Chart** (ESRI Ocean + OpenSeaMap), **Minimal**
  - Asynchronous tile caching engine for offline maritime operations
- **Figma-Style Floating Canvas Toolbar**:
  - Dark glassmorphic floating tool dock anchored over bottom radar canvas
  - Tools: **Pan (`H`)** [safe default], **Target Waypoint (`W`)**, **Keep-Out Boundary (`P`)**, **Hazard Buoy (`B`)**, **Tactical Ruler (`M`)**, **Recenter (`R`)**
- **Live Video Feed & Multi-Monitor Support**:
  - FPV / Gimbal camera with Daylight (EO), Thermal IR, and Night Vision modes
  - Artificial horizon, pitch ladder, compass tape, and live hydrophone audio VU meter
  - Draggable Picture-in-Picture (PiP) dockable anywhere on the radar canvas
  - **Multi-Monitor Pop-Out (`⤢`)**: Detach video feed into an independent top-level window to drag onto a secondary display/monitor, with one-click re-docking (`↙`)
- **Obstacle Management & Decentralized Autonomy**:
  - Live right-click placement and interactive drag-and-drop repositioning for buoys and shoals
  - Real-time Artificial Potential Field (APF) obstacle repulsion and dynamic `AVOIDING` telemetry state
  - Forward-looking perception sensor cone with automatic obstacle discovery and 4m spatial clustering
- **Keep-Out Boundaries & Geofences**:
  - Multi-vertex polygon drawing tool with live rubber-band preview and origin snap-to-close
  - Crimson warning fill, perimeter dashed stroke, and autonomous APF repulsive boundary deflection
- **Swarm Fleet Dashboard**:
  - Real-time telemetry table for each USV (Coordinates, Speed, Battery %, Operational State)
  - Dynamic fleet size scaling (2 to 6 USVs)
  - Aggregate fleet metrics (Average Battery, Swarm Center of Mass)
- **Formation & Mission Control**:
  - **Formation Types**: V-Shape (Chevron), Line (Abeam), Column (In-line), Circle (Encirclement), Diamond
  - **Dynamic Parameters**: Vehicle spacing slider (5m - 50m) and Bearing / Heading slider (0° - 359°)
  - **Mission Actions**: Deploy Formation, Hold / Disperse, Return to Home (RTH), and Emergency Stop (ESTOP)
  - **Swarm Physics Simulator**: Built-in kinematic steering model for zero-hardware desktop testing
- **Dual Operation Modes**:
  - **Standalone Simulation (`🎮`)**: Built-in 2D kinematic and hydrodynamic physics engine with APF navigation for desktop testing with zero external dependencies.
  - **External ROS 2 / Hardware (`📡`)**: Real-time bridge that suspends synthetic kinematics and ingests live vehicle odometry, telemetry, and camera streams from simulators (Isaac Sim, Gazebo, MuJoCo, Simulink) or physical USV companion computers.
- **Dynamic Multi-Vehicle Auto-Discovery**:
  - Automatically discovers newly appearing `/usv_{id}/*` namespaces on the ROS 2 topic graph at runtime, registering new fleet cards and radar glyphs dynamically.
- **Standardized ROS 2 Integration**:
  - Seamlessly integrates PyQt5 event loop with `rclpy` (50 Hz spin)
  - **Fleet & Swarm Broadcasts**:
    - `/ground_station/formation_cmd` (`std_msgs/String` - JSON payload with target slots, spacing, bearing)
    - `/ground_station/emergency_stop` (`std_msgs/Bool`)
    - `/ground_station/heartbeat` (`std_msgs/String` - 1 Hz system heartbeat)
    - `/ground_station/geofence` (`geometry_msgs/PolygonStamped` - Keep-out zone vertices)
    - `/ground_station/detected_obstacles` (`visualization_msgs/MarkerArray` or JSON)
  - **Per-USV Downlinks (Command & Control)**:
    - `/usv_{id}/target_pose` (`geometry_msgs/PoseStamped` - Downlink target slot coordinate & orientation)
    - `/usv_{id}/autonomy_mode` (`std_msgs/String` - `FORMATION`, `TRANSIT`, `HOLD`, `RTH`, `MANUAL`)
    - `/usv_{id}/cmd_vel` (`geometry_msgs/Twist` - Manual teleop joystick/keyboard direct drive with auto-zero stop)
  - **Per-USV Uplinks (Telemetry Ingestion)**:
    - `/usv_{id}/odom` (`nav_msgs/Odometry` - Real-time position, orientation quaternion, and linear/angular velocity)
    - `/usv_{id}/battery` (`sensor_msgs/BatteryState` - State of charge percentage and bus voltage)
    - `/usv_{id}/sensors/sonar` (`sensor_msgs/Range` - Forward obstacle / bathymetric depth range)
    - `/usv_{id}/camera/image_raw/compressed` (`sensor_msgs/CompressedImage` - Live JPEG compressed FPV camera stream)
  - Telemetry & event log console

---

## Quick Start (macOS Apple Silicon & Linux)

### 1. Launch the Ground Station GUI

From the project root:

```bash
pixi run run
```

Alternatively, if you are inside an active `pixi shell`:

```bash
source install/setup.zsh
ros2 run ground_station ground_station_node
```

### 2. Verify ROS 2 Topics

In a separate terminal:

```bash
pixi shell
ros2 topic list
```

To monitor formation commands published by the GUI:

```bash
ros2 topic echo /ground_station/formation_cmd
```
