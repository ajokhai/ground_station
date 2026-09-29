"""
MuJoCo Physics — USV Simulation Bridge
=====================================
Integrates DeepMind MuJoCo physics engine with the USV Ground Station
using the lightweight `usv_sdk` package.

Usage:
    python sim_bridges/mujoco/mujoco_usv_bridge.py --usv-id usv_1
    python sim_bridges/mujoco/mujoco_usv_bridge.py --usv-id usv_1 --gui
"""

import argparse
import os
import math
import sys
import time

try:
    import mujoco
    import mujoco.viewer
    MUJOCO_AVAILABLE = True
except ImportError:
    MUJOCO_AVAILABLE = False

try:
    from usv_sdk import USVAgent, AutonomyMode, TargetPose
    SDK_AVAILABLE = True
except ImportError:
    # Fallback to local import if run without installation
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from usv_sdk import USVAgent, AutonomyMode, TargetPose
    SDK_AVAILABLE = True


def run_mujoco_bridge(usv_id: str, use_gui: bool = False):
    if not MUJOCO_AVAILABLE:
        print("[MuJoCo Bridge] The 'mujoco' Python library was not found.")
        print("To run with full rigid-body dynamics, install via:")
        print("  pip install mujoco")
        return

    xml_path = os.path.join(os.path.dirname(__file__), "usv_scene.xml")
    if not os.path.exists(xml_path):
        print(f"[MuJoCo Bridge] Model file not found at: {xml_path}")
        return

    print(f"Loading MuJoCo model from: {xml_path}")
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)

    # Initialize USVAgent client
    agent = USVAgent(usv_id=usv_id)
    agent.start_async()

    # Teleoperation and autonomy control cache
    control_state = {
        "surge_force": 0.0,
        "yaw_moment": 0.0,
        "last_cmd_time": time.time(),
        "battery": 98.5
    }

    @agent.on_cmd_vel
    def _on_cmd_vel(linear_x: float, angular_z: float):
        control_state["surge_force"] = linear_x * 80.0     # ~240 N
        control_state["yaw_moment"] = angular_z * 40.0     # Differential thrust
        control_state["last_cmd_time"] = time.time()

    @agent.on_emergency_stop
    def _on_estop():
        control_state["surge_force"] = 0.0
        control_state["yaw_moment"] = 0.0

    print(f"✅ MuJoCo USV Bridge online for '{usv_id}'. Streaming to USV Ground Station.")

    def _physics_step():
        # Check command failsafe
        if time.time() - control_state["last_cmd_time"] > 1.0:
            control_state["surge_force"] *= 0.92
            control_state["yaw_moment"] *= 0.92

        # Differential thruster mixing:
        # ctrl[0] = Port thruster, ctrl[1] = Starboard thruster
        t_port = control_state["surge_force"] + control_state["yaw_moment"]
        t_stbd = control_state["surge_force"] - control_state["yaw_moment"]

        data.ctrl[0] = max(-150.0, min(250.0, t_port))
        data.ctrl[1] = max(-150.0, min(250.0, t_stbd))

        # Hydrodynamic damping on planar velocity
        data.qvel[0] *= 0.985  # Surge damping
        data.qvel[1] *= 0.920  # Sway damping
        data.qvel[5] *= 0.940  # Yaw rate damping

        # Restrict heave, roll, pitch to water surface plane
        data.qpos[2] = 0.05
        data.qvel[2] = 0.0

        mujoco.mj_step(model, data)

        # Read root body state
        x = float(data.qpos[0])
        y = float(data.qpos[1])
        qw, qx, qy, qz = data.qpos[3], data.qpos[4], data.qpos[5], data.qpos[6]
        yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
        speed = math.hypot(data.qvel[0], data.qvel[1])
        yaw_rate = float(data.qvel[5])

        # Publish to ROS 2 topics
        agent.publish_odom(x=x, y=y, heading=yaw, speed=speed, yaw_rate=yaw_rate)

        control_state["battery"] = max(5.0, control_state["battery"] - 0.0001)
        agent.publish_battery(soc_pct=control_state["battery"], voltage=24.4)
        agent.publish_sonar(range_m=18.0)

    try:
        if use_gui:
            with mujoco.viewer.launch_passive(model, data) as viewer:
                while viewer.is_running():
                    step_start = time.time()
                    _physics_step()
                    viewer.sync()
                    elapsed = time.time() - step_start
                    time.sleep(max(0.001, model.opt.timestep - elapsed))
        else:
            dt = model.opt.timestep
            while True:
                step_start = time.time()
                _physics_step()
                elapsed = time.time() - step_start
                time.sleep(max(0.001, dt - elapsed))

    except KeyboardInterrupt:
        print("\nStopping MuJoCo bridge...")
    finally:
        agent.shutdown()


def main():
    parser = argparse.ArgumentParser(description="MuJoCo USV Physics Simulation Bridge")
    parser.add_argument("--usv-id", default="usv_1", help="USV identifier namespace")
    parser.add_argument("--gui", action="store_true", help="Launch interactive 3D viewer")
    args = parser.parse_args()

    run_mujoco_bridge(args.usv_id, args.gui)


if __name__ == "__main__":
    main()
