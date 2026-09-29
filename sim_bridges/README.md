# USV Ground Station — Reference Simulator Connectors

This directory provides working reference connectors, bridge templates, and mathematical models for linking the **USV Ground Station** with industry-leading simulation platforms:

1. **[NVIDIA Isaac Sim](isaac_sim/)**: RTX GPU-accelerated water surface physics, multi-camera synthetic perception, and Omniverse ActionGraph ROS 2 bridge.
2. **[MATLAB / Simulink](simulink/)**: Fossen 6-DOF nonlinear marine hydrodynamic equations of motion, thruster dynamics, and ROS Toolbox integration.
3. **[MuJoCo Physics](mujoco/)**: Lightweight rigid-body marine hull simulation, buoyancy integration, and real-time ROS 2 state broadcasting.

---

## Architecture Overview

All connectors adhere strictly to the Ground Station's standard topic contract:

```
┌────────────────────────────────────────────────────────┐
│                   USV Ground Station                   │
│   (Mode: 📡 External ROS 2 / Hardware)                 │
└──────────────┬──────────────────────────▲──────────────┘
               │                          │
   Downlinks   │                          │   Uplinks
   (/target_pose, /cmd_vel,              │   (/odom, /battery,
    /autonomy_mode, /geofence)           │    /sonar, /camera)
               │                          │
               ▼                          │
┌─────────────────────────────────────────┴──────────────┐
│                  Simulation Engine                     │
│   (NVIDIA Isaac Sim / Simulink / MuJoCo / Gazebo)      │
└────────────────────────────────────────────────────────┘
```
