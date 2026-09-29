# MuJoCo USV Physics Simulation Bridge

This connector integrates **DeepMind's MuJoCo physics engine** with the **USV Ground Station** via the `usv_sdk` Python client.

---

## Capabilities

- **Rigid-Body Hydrodynamics**: Models catamaran multi-hull physics, inertial coupling, hydrodynamic fluid drag, and twin differential thruster dynamics.
- **Bi-Directional ROS 2 Streaming**:
  - Ingests direct manual teleoperation `/usv_{id}/cmd_vel` or autonomous waypoints `/usv_{id}/target_pose`.
  - Publishes real-time kinematic state to `/usv_{id}/odom`.
  - Reports battery discharge and acoustic depth soundings.
- **Fast Headless or Interactive Visualizer**: Step physics at up to 500 Hz for high-speed reinforcement learning and GNC controller validation.

---

## Installation

Ensure your Python environment has MuJoCo installed:

```bash
pip install mujoco
```

---

## Running the MuJoCo Bridge

From the workspace root:

```bash
python sim_bridges/mujoco/mujoco_usv_bridge.py --usv-id usv_1
```

To run with interactive 3D GLFW viewer:

```bash
python sim_bridges/mujoco/mujoco_usv_bridge.py --usv-id usv_1 --gui
```

Then in the Ground Station toolbar, set the operation mode to **`📡 External ROS 2 / Hardware`** to observe MuJoCo physics driving the tactical radar!
