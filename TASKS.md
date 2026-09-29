# USV Ground Station — Multi-Platform Autonomy & Simulation Roadmap

This document outlines the master implementation plan, technical specifications, and task tracking matrix for extending the **USV Ground Station** into an industry-grade Command & Control (C2) platform compatible with **NVIDIA Isaac Sim**, **MATLAB/Simulink**, **MuJoCo**, and **physical USV fleets**.

---

## Architecture Principles

1. **Strategic C2 vs. Tactical Autonomy**:
   - The Ground Station manages fleet coordination, formation geometries, mission corridors, and high-level waypoints.
   - Onboard USV systems (simulated or real) handle local guidance, navigation, control (GNC), dynamic obstacle avoidance (COLREGS), and low-level thruster allocation.
2. **Standardized ROS 2 Messaging**:
   - Standard robotics message types (`nav_msgs`, `sensor_msgs`, `geometry_msgs`, `visualization_msgs`) ensure identical interfaces across Isaac Sim, Simulink, MuJoCo, and physical companion computers (NVIDIA Jetson, Raspberry Pi).
3. **Dual Coordinate System (WGS84 $\leftrightarrow$ Local ENU)**:
   - Operators can plan missions and view telemetry seamlessly in both real-world GPS coordinates (Latitude/Longitude) and local high-precision Cartesian coordinates (East-North-Up meters).
4. **Multi-Layer Environmental Mapping**:
   - Support for vector radar HUD, high-resolution satellite imagery, nautical electronic navigational charts (ENC/OpenSeaMap), and 2D occupancy costmaps.

---

## Task Breakdown Structure (WBS) & Status Matrix

### Legend
- `[x]` Completed
- `[/]` In Progress
- `[ ]` Planned / Queued

### Phase Status Overview

| Phase | Description | Status | Progress |
| :--- | :--- | :---: | :---: |
| **Phase 1** | Georeferencing & Environmental Map Layers (Satellite, Charts, Datum) | **Complete** | `100% (3/3)` `[x]` |
| **Phase 2** | Decentralized Autonomy, APF Avoidance, Geofencing & Downlink ROS 2 Topics | **Complete** | `100% (3/3)` `[x]` |
| **Phase 3** | External Simulator & Hardware ROS 2 Ingestion Bridge | **Complete** | `100% (3/3)` `[x]` |
| **Phase 4** | USV Fleet Python SDK & Reference Simulator Connectors | **Complete** | `100% (5/5)` `[x]` |
| **Phase 5** | Mission Planning & Field Operations Tools (Survey Patterns, Bathymetry) | Planned | `0% (0/3)` `[ ]` |


---

### Phase 1: Georeferencing & Environmental Map Layers

Enables real-world GPS navigation, geographic datum reference, and multi-layer map rendering.

- [x] **1.1 Georeferencing Engine (`ground_station/core/georeference.py`)**
  - [x] Implement WGS84 ellipsoidal to local East-North-Up (ENU) Cartesian projection without heavy external GIS dependencies.
  - [x] Support configurable Datum Reference Point (`datum_lat`, `datum_lon`, `datum_alt`).
  - [x] Bi-directional conversions: `(lat, lon) <-> (x_meters, y_meters)`.
  - [x] Format helpers for Decimal Degrees (DD), Degrees-Minutes-Seconds (DMS), and MGRS/UTM.

- [x] **1.2 Radar Canvas Geographic Integration (`radar_widget.py`)**
  - [x] Display live GPS coordinates under the cursor alongside local meter coordinates.
  - [x] Georeference Datum Reference Anchor icon and coordinates rendered at world (0, 0).
  - [x] Dynamic scale bar (Metric meters & Nautical Miles / Feet).
  - [x] Target waypoint GPS coordinate calculation and status bar readout.

- [x] **1.3 Map Layer Switcher & Rendering Engine (`ground_station/core/tile_manager.py` & `radar_widget.py`)**
  - [x] Expand Toolbar Map Style selector: `Grid`, `Tactical`, `Satellite`, `Nautical Chart`, `Minimal`.
  - [x] Asynchronous tile fetcher & disk cache (`~/.cache/usv_ground_station/tiles/{layer}/{z}/{x}/{y}.png`) for offline field operations.
  - [x] Support for ESRI World Imagery (Satellite) and ESRI World Ocean Base + OpenSeaMap (Nautical Chart).
  - [x] Blit tiles seamlessly underneath vector radar elements with opacity control and tactical graticule overlay.
  - [x] **15 Global Sea Ports & Coastal Operations Presets (`datum_dialog.py`)**: Instant theater selection for major naval/maritime hubs (San Francisco Bay, Rotterdam, Singapore, Sydney, Portsmouth, Gibraltar, etc.).
  - [x] **Interactive Maritime Datum Dialog (`Ctrl+Shift+D`)**: Searchable category filters (`⚓ Sea Ports`, `🌊 Open Ocean`) and custom WGS84 coordinates.
  - [x] **Adaptive Zoom Downscaling**: Real-time tile downsampling preventing map blanking at high altitudes.

---

### Phase 2: Decentralized Autonomy & Obstacle Avoidance Pipeline

Empowers USVs to report local autonomy states, detected hazards, and dynamic path deviations back to the Ground Station.

- [x] **2.1 Standardized Autonomy Topic Schema & Auto-Detection Ingestion**
  - [x] Uplink subscriber: `/ground_station/detected_obstacles` (`visualization_msgs/MarkerArray` or JSON) in `ground_station_node.py`.
  - [x] Operator-controlled and ROS 2-ingested marine hazard tracking (no spontaneous synthetic obstacle generation).
  - [x] Downlink: `/usv_{id}/target_pose` (`geometry_msgs/PoseStamped`) for assigned formation slot or waypoint.
  - [x] Downlink: `/usv_{id}/autonomy_mode` (`std_msgs/String`) — `FORMATION`, `TRANSIT`, `HOLD`, `RTH`, `MANUAL`.
  - [x] Dynamic formation re-engagement & state recovery from `AVOIDING` / `HOLD` when adjusting formation layout or target waypoints.
  - [x] ROS 2 topic namespace normalization (`USV-1` -> `usv_1`) adhering strictly to standard naming conventions.

- [x] **2.2 Radar Canvas Obstacle Visualization & Interactive Management**
  - [x] Render dynamic obstacle halos (Amber = Caution buffer, Red = Hazard buffer) on the radar.
  - [x] **Interactive Right-Click Placement**: Context menu to place buoys (5m), shoals (8m), custom hazards, or set GPS datum.
  - [x] **Interactive Drag & Drop**: Left-click and drag any hazard circle live on the map to test swarm re-routing.
  - [x] **Right-Click Obstacle Menu**: Edit radius/label, toggle hazard/caution, or delete obstacle.
  - [x] Visual sensor badges (`📡 [USV-1]`) distinguishing auto-detected hazards from manual waypoints.
  - [x] Real-time Artificial Potential Field (APF) local obstacle repulsion loop in navigation engine.
  - [x] Dynamic `AVOIDING` telemetry state tracking when USVs deviate to clear hazards.

- [x] **2.3 Floating Canvas Toolbar, Keep-Out Zones & Geofencing Tool**
  - [x] **Figma-Style Floating Tool Dock (`CanvasToolbar`)**:
    - [x] Anchored over bottom radar canvas with dark glassmorphic styling (`#121216`, `#27272a`).
    - [x] Safe default **Pan Mode (`H`)** preventing accidental formation relocation on map clicks.
    - [x] Tool switcher: **Pan (`H`)**, **Target Waypoint (`W`)**, **Boundary (`P`)**, **Hazard Buoy (`B`)**, **Ruler Measure (`M`)**, **Recenter (`R`)**.
    - [x] Fixed geometry and layout padding (`515x42px`, `30px` pill buttons) eliminating text clipping and label truncation.
    - [x] Repositioned video PiP monitor to top-right to preserve canvas floor clearance.
    - [x] Scoped drag-and-drop interactions exclusively to Pan mode to prevent tool conflicts.
  - [x] **Draggable Video PiP & Multi-Monitor Pop-Out Window**:
    - [x] Free canvas dragging by header bar with tactical grip handle (`⠿`), persistent custom position, and canvas boundary clamping.
    - [x] Pop-out button (`⤢`) to detach the live video feed into an independent top-level OS window that can be moved across external monitors and physical displays.
    - [x] One-click docking (`↙`) to re-embed the detached video window seamlessly back into the radar canvas.
  - [x] **Keep-Out Boundary Drawing & Management**:
    - [x] Multi-vertex polygon drawing tool with live rubber-band preview and origin snap-to-close (`14px` radius).
    - [x] Translucent crimson warning fill (`rgba(239, 68, 68, 0.14)`), dashed perimeter stroke, corner anchor vertices, and name badge tags.
    - [x] Right-click boundary context menu: Rename, Delete, Clear All Boundaries.
    - [x] Autonomous Artificial Potential Field (APF) boundary repulsive deflection in simulation engine.
    - [x] Broadcast geofences via ROS 2 `/ground_station/geofence` (`geometry_msgs/PolygonStamped`) with transient local QoS.
  - [x] **Tactical Distance & Bearing Ruler**:
    - [x] Click-to-measure tool showing live dashed line, crosshair end caps, and midpoint HUD badge.
    - [x] Real-time metric distance ($m$ / $km$), nautical miles ($NM$), and true compass bearing ($^\circ T$).
  - [x] **Integrated In-App User Guide & Help Center (`help_dialog.py`)**:
    - [x] App Menu **Help** section (`F1`, `Ctrl+/`) with searchable topic guide, keyboard shortcuts matrix, and ROS 2 topic architecture specifications.
    - [x] Real USV & Simulator Integration section (Section 9: topic contracts, dynamic discovery flow, DDS domain configuration, CLI verification).
    - [x] Maritime Operational Areas & GPS Datum Dialog documentation (`Ctrl+Shift+D`).
    - [x] Direct keyboard teleoperation reference (`W`/`A`/`S`/`D`, `Space` brake) and video visibility toggling.




---

### Phase 3: External Simulator & Hardware ROS 2 Ingestion Bridge

Allows the Ground Station to switch smoothly between standalone internal testing and live external data streams.

- [x] **3.1 Simulation Mode Selector**
  - [x] Toolbar operation mode switcher: `🎮 Standalone Simulation` vs `📡 External ROS 2 / Hardware`.
  - [x] Real-time visual status badge in the application status bar (`🎮 SIMULATION` / `📡 EXTERNAL ROS 2`).
  - [x] In External Mode, internal Euler kinematics simulation is bypassed while live `/usv_{id}/odom` positions are ingested directly into the radar HUD.
  - [x] Downlink telemetry broadcasts (`/usv_{id}/target_pose` and `/usv_{id}/autonomy_mode`) continue reliably at 5 Hz across all operation modes.

- [x] **3.2 ROS 2 Telemetry Subscriptions (`ground_station_node.py`)**
  - [x] Dynamic multi-agent subscriber pool for $N$ vehicles:
    - `nav_msgs/msg/Odometry` (`/usv_{id}/odom`) — vehicle position, heading, velocity.
    - `sensor_msgs/msg/BatteryState` (`/usv_{id}/battery`) — battery SOC percentage and bus voltage.
    - `sensor_msgs/msg/Range` (`/usv_{id}/sensors/sonar`) — forward depth / obstacle range.
    - `sensor_msgs/msg/CompressedImage` (`/usv_{id}/camera/image_raw/compressed`) — real-time JPEG compressed FPV video feed with VideoPiP integration.
  - [x] Automatic USV dynamic discovery: Periodic ROS 2 topic graph scanner (1.5 Hz) detecting new `/usv_{id}/*` namespaces and binding subscribers automatically.
  - [x] Dynamic UI fleet card & radar marker registration for newly discovered external vessels.

- [x] **3.3 Manual Joystick & Override Publisher**
  - [x] Publish direct velocity commands (`geometry_msgs/msg/Twist`) to `/usv_{id}/cmd_vel` during keyboard teleoperation (W/A/S/D / Arrows).
  - [x] Automatic zero-velocity safety stop command `(0.0, 0.0)` broadcasted upon teleop disengagement or Emergency Stop (`Space`).

---

### Phase 4: USV Fleet Python SDK & Reference Simulator Connectors

Provides a dedicated developer SDK (`usv_sdk`) and working reference adapters for researchers and developers integrating autonomous vessels or simulation environments.

- [x] **4.1 USV Fleet Python SDK (`usv_sdk/`)**
  - [x] Standalone lightweight Python client library (`USVAgent`) for zero-boilerplate vehicle onboarding.
  - [x] Built-in topic binding: automatically consumes `/usv_{id}/target_pose`, `/usv_{id}/autonomy_mode`, `/usv_{id}/cmd_vel`, `/ground_station/emergency_stop`, and `/ground_station/geofence`.
  - [x] Out-of-the-box telemetry dispatcher: helper methods to publish `/usv_{id}/odom`, `/usv_{id}/battery`, `/usv_{id}/sensors/sonar`, and `/ground_station/detected_obstacles`.
  - [x] Event-driven callbacks: `@agent.on_target_pose`, `@agent.on_mode_change`, `@agent.on_cmd_vel`, `@agent.on_emergency_stop`, `@agent.on_geofence_update`.
  - [x] Swarm test harness: scriptable CLI to instantiate $N$ mock USV agents for load and formation testing (`python -m usv_sdk.cli swarm`).
  - [x] Comprehensive SDK documentation, API reference, and quickstart examples (`usv_sdk/README.md`).

- [x] **4.2 Standalone Reference USV Node (`usv_agent_node.py`)**
  - [x] Lightweight ROS 2 Python node acting as an autonomous USV powered by `usv_sdk`.
  - [x] Subscribes to `/usv_{id}/target_pose` and `/usv_{id}/autonomy_mode` from the Ground Station.
  - [x] Implements local Artificial Potential Field (APF) obstacle avoidance and boundary repulsion.
  - [x] Publishes actual `/usv_{id}/odom`, `/battery`, and `/sensors/sonar`.
  - [x] Registered console script `usv_agent_node` executable on Jetson, Raspberry Pi, or desktop.

- [x] **4.3 NVIDIA Isaac Sim Connector (`sim_bridges/isaac_sim/`)**
  - [x] USD scene setup guide and Omniverse ActionGraph ROS 2 bridge template (`sim_bridges/isaac_sim/README.md`).
  - [x] Standalone runner script (`isaac_sim_bridge.py`) mapping Isaac Sim RTX water physics and camera sensors to standard USV topics.

- [x] **4.4 MATLAB / Simulink Connector (`sim_bridges/simulink/`)**
  - [x] Fossen 6-DOF nonlinear marine hydrodynamic equations of motion (`fossen_6dof_model.m`).
  - [x] Subscribes to `/usv_{id}/cmd_vel`, integrates Coriolis, added mass, and drag, and publishes `/usv_{id}/odom`.
  - [x] Architectural documentation and integration guide (`sim_bridges/simulink/README.md`).

- [x] **4.5 MuJoCo Connector (`sim_bridges/mujoco/`)**
  - [x] High-speed catamaran multi-hull physics model (`usv_scene.xml`) with differential thruster actuators and hydrodynamic damping.
  - [x] Python runner script (`mujoco_usv_bridge.py`) stepping MuJoCo physics and bridging state to ROS 2 topics via `usv_sdk`.
  - [x] Headless and interactive GLFW 3D viewer support (`sim_bridges/mujoco/README.md`).

---

### Phase 5: Mission Planning & Field Operations Tools

Advanced tooling for operational deployment in open water.

- [ ] **5.1 Search & Survey Pattern Generator**
  - [ ] Lawnmower / Parallel track generator for hydrographic surveying or search-and-rescue.
  - [ ] Dynamic corridor assignment across the USV swarm.

- [ ] **5.2 Bathymetry Live Heatmap**
  - [ ] Live seabed depth color contour raster generated from reported sonar depth soundings.

- [ ] **5.3 Mission Log & Playback**
  - [ ] Rosbag2 recording & playback integration directly from the Ground Station UI.

---

## Standard ROS 2 Topic Architecture

```
/ground_station/
  ├── formation_cmd       [std_msgs/msg/String]
  ├── emergency_stop      [std_msgs/msg/Bool]
  ├── heartbeat           [std_msgs/msg/String]
  ├── geofence            [geometry_msgs/msg/PolygonStamped]
  └── metocean            [geometry_msgs/msg/TwistStamped]

/usv_{id}/
  ├── target_pose         [geometry_msgs/msg/PoseStamped]       (GCS -> USV)
  ├── autonomy_mode       [std_msgs/msg/String]                 (GCS -> USV)
  ├── cmd_vel             [geometry_msgs/msg/Twist]             (GCS -> USV, Manual)
  ├── odom                [nav_msgs/msg/Odometry]               (USV -> GCS)
  ├── autonomy_status     [std_msgs/msg/String]                 (USV -> GCS)
  ├── detected_obstacles  [visualization_msgs/msg/MarkerArray]  (USV -> GCS)
  ├── battery             [sensor_msgs/msg/BatteryState]        (USV -> GCS)
  ├── camera/
  │   └── image_raw       [sensor_msgs/msg/CompressedImage]     (USV -> GCS)
  └── sensors/
      ├── sonar           [sensor_msgs/msg/Range]               (USV -> GCS)
      └── metocean        [geometry_msgs/msg/TwistStamped]      (USV -> GCS)
```
