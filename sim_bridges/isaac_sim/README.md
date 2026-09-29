# NVIDIA Isaac Sim USV Connector

This connector integrates **NVIDIA Isaac Sim (2023.1+ / 4.0+)** with the **USV Ground Station** using the native Omniverse `omni.isaac.ros2_bridge` extension.

---

## Capabilities

- **GPU-Accelerated Water Physics**: Realistic buoyancy and wave-craft interaction using NVIDIA PhysX.
- **Synthetic Sensor Streaming**:
  - Live masthead FPV camera stream published to `/usv_{id}/camera/image_raw/compressed` (streamed directly into the Ground Station Video PiP).
  - Forward acoustic/LiDAR rangefinder soundings published to `/usv_{id}/sensors/sonar`.
  - True vehicle kinematics published to `/usv_{id}/odom`.
- **Closed-Loop Actuation**:
  - Subscribes to `/usv_{id}/cmd_vel` for direct teleoperation.
  - Subscribes to `/usv_{id}/target_pose` for autonomous waypoint pursuit.

---

## ActionGraph ROS 2 Bridge Configuration

Within the Isaac Sim Stage Editor:

1. **Enable Extension**: Navigate to **Window &rarr; Extensions** and enable `omni.isaac.ros2_bridge`.
2. **Create ActionGraph**: Create an ActionGraph under `/World/ActionGraph`:
   - `On Playback Tick` &rarr; `ROS2 Context` (set `domain_id: 0`).
   - `ROS2 Publish Odometry`:
     - Target Prim: `/World/USV_1/base_link`
     - Topic: `/usv_1/odom`
     - Frame: `world`, Child Frame: `usv_1_base_link`
   - `ROS2 Camera Helper`:
     - Render Product: Masthead Camera Prim
     - Topic: `/usv_1/camera/image_raw/compressed`
     - Type: `rgb`, Format: `jpeg`
   - `ROS2 Subscribe Twist`:
     - Topic: `/usv_1/cmd_vel`
     - Target: USV differential thruster physics driver or articulation controller.

---

## Standalone Python Runner

You can also run Isaac Sim headlessly or with GUI via the standalone script:

```bash
./isaac-sim.python.sh sim_bridges/isaac_sim/isaac_sim_bridge.py --usv-id usv_1 --headless
```
