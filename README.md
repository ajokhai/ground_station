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
  - **Planetary Multi-Scale Zoom (Zoom 1 - 19)**: Unrestricted zoom architecture scaling smoothly from tactical berth level (50 px/m) out to full globe overview (Zoom 1, scale $0.000008\text{ px/m}$) with adaptive graticule spacing and kilometer / nautical mile readouts.
  - **Global Place Search & Natural Language Geocoding (`Ctrl+F`)**: Integrated toolbar search bar powered by OpenStreetMap Nominatim and an offline strategic port database (50+ maritime choke points). Instantly parses raw GPS coordinates or natural language place names to re-anchor datum and recenter the canvas.
  - **Real-Time Live Metocean & Weather Ingestion**: Automated background service querying Open-Meteo Forecast & Marine APIs (zero API-key requirement) to deliver live surface wind (speed, direction, gusts), wave height, wave period, barometric pressure, and temperature for the active operational theater.
  - **15 Global Sea Ports & Coastal Operations Presets**: Pre-configured operational areas (San Francisco Bay, Port of Rotterdam, Port of Singapore, Sydney Harbour, Portsmouth Naval Base, Strait of Gibraltar, Panama Canal, etc.)
  - **Interactive Datum Dialog (`Ctrl+Shift+D`)**: Searchable dialog with category filters (`⚓ Sea Ports`, `🌊 Open Ocean`) and custom Lat/Lon coordinate re-anchoring
  - Tile switcher: **Grid**, **Tactical**, **Satellite** (ESRI World Imagery), **Nautical Chart** (ESRI Ocean + OpenSeaMap), **Minimal**
  - Adaptive zoom downscaling engine to prevent tile blanking at high altitudes
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

---

## Adding a Real USV or External Simulator

Connecting physical USV companion computers (NVIDIA Jetson, Raspberry Pi) or simulators (NVIDIA Isaac Sim, Gazebo, MuJoCo, MATLAB/Simulink) requires zero code modifications:

1. **Network Configuration**: Ensure both the Ground Station and the robot/simulator share the same network subnet and ROS 2 domain:
   ```bash
   export ROS_DOMAIN_ID=0  # match your fleet's domain ID
   ```
2. **Switch Operation Mode**: In the Ground Station top toolbar, switch the mode dropdown to **`📡 External ROS 2 / Hardware`**.
3. **Publish Odometry**: On your vehicle or simulator node, publish to standard namespace topics:
   - `/usv_1/odom` (`nav_msgs/Odometry`)
   - `/usv_1/battery` (`sensor_msgs/BatteryState`, optional)
   - `/usv_1/sensors/sonar` (`sensor_msgs/Range`, optional)
   - `/usv_1/camera/image_raw/compressed` (`sensor_msgs/CompressedImage`, optional)
4. **Dynamic Auto-Discovery**: The Ground Station automatically registers `/usv_1` within 1.5 seconds, creates a telemetry card in the sidebar, and places its vessel glyph on the tactical radar.
5. **Teleoperate or Command**:
   - **Manual Drive**: Click a USV to select it and drive with `W`/`A`/`S`/`D` or Arrow keys (broadcasts `/usv_{id}/cmd_vel` with auto-zero stop on release).
   - **Autonomous Swarm**: Click **Deploy Swarm** (`Ctrl+D`) to dispatch target slot waypoints over `/usv_{id}/target_pose`.

---

## USV Fleet Python SDK (`usv_sdk`)

The repository includes a standalone, lightweight ROS 2 Python client library (`usv_sdk`) designed for rapid deployment onto physical companion computers or simulator wrappers:

```python
from usv_sdk import USVAgent, TargetPose

# Instantiate agent for USV namespace
agent = USVAgent(usv_id="usv_1")

# Register waypoint target handler
@agent.on_target_pose
def handle_target(target: TargetPose):
    print(f"Assigned slot: ({target.x:.1f}, {target.y:.1f})")

agent.start_async()
agent.publish_odom(x=15.0, y=30.0, heading=1.57, speed=2.8)
agent.publish_battery(soc_pct=96.0, voltage=25.2)
```

### Instant Swarm Simulator CLI (`usv_swarm_sim`)

Spin up an autonomous multi-vehicle swarm for load testing directly from the command line:

```bash
# Spawn a 4-vehicle autonomous swarm with 20m separation
pixi run ros2 run ground_station usv_swarm_sim swarm --count 4 --spacing 20.0

# Or run single autonomous reference agent with APF avoidance
pixi run ros2 run ground_station usv_agent_node --ros-args -p usv_id:=usv_1 -p initial_x:=10.0 -p initial_y:=15.0
```

---

## Reference Simulator Connectors (`sim_bridges/`)

Ready-to-use bridge scripts and hydrodynamic models located in [`sim_bridges/`](sim_bridges/):

- **[NVIDIA Isaac Sim](sim_bridges/isaac_sim/)**: RTX water simulation, ActionGraph ROS 2 bridge, and synthetic camera streaming.
- **[MATLAB / Simulink](sim_bridges/simulink/)**: Thor I. Fossen 6-DOF nonlinear hydrodynamic ODE model with Coriolis, added mass, and twin thruster dynamics.
- **[MuJoCo Physics](sim_bridges/mujoco/)**: Rigid-body catamaran MJCF model (`usv_scene.xml`) with hydrodynamic damping and interactive 3D viewer.

---

## Built-In Documentation & Shortcuts

Press **`F1`** inside the application to open the comprehensive dark-mode **User Guide & Reference**, featuring full architectural explanations, tactical radar guides, interactive hazard APF tutorials, and keyboard shortcuts.

