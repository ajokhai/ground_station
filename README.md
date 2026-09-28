# HERMORD USV Ground Station

A ROS 2 Humble ground station package for managing, coordinating, and monitoring Unmanned Surface Vehicle (USV) swarm formations.

## Features

- **Tactical 2D Radar & Map Display**:
  - Live USV vessel glyphs with real-time headings and trajectory trails
  - Concentric range rings (meters) and radar sweep animation
  - Interactive target formation geometry overlay (ghost markers and connecting formation lines)
  - Interactive waypoint designation (click anywhere on radar to designate target center)
  - Zoom (wheel / buttons) and Pan (middle-click or shift-drag)
- **Swarm Fleet Dashboard**:
  - Real-time telemetry table for each USV (Coordinates, Speed, Battery %, Operational State)
  - Dynamic fleet size scaling (2 to 6 USVs)
  - Aggregate fleet metrics (Average Battery, Swarm Center of Mass)
- **Formation & Mission Control**:
  - **Formation Types**: V-Shape (Chevron), Line (Abeam), Column (In-line), Circle (Encirclement), Diamond
  - **Dynamic Parameters**: Vehicle spacing slider (5m - 50m) and Bearing / Heading slider (0° - 359°)
  - **Mission Actions**: Deploy Formation, Hold / Disperse, Return to Home (RTH), and Emergency Stop (ESTOP)
  - **Swarm Physics Simulator**: Built-in kinematic steering model for zero-hardware desktop testing
- **ROS 2 Integration**:
  - Seamlessly integrates PyQt5 event loop with `rclpy` (50 Hz spin)
  - Publishes:
    - `/ground_station/formation_cmd` (`std_msgs/String` - JSON payload with target slots, spacing, bearing)
    - `/ground_station/emergency_stop` (`std_msgs/Bool`)
    - `/ground_station/heartbeat` (`std_msgs/String` - 1 Hz system heartbeat)
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