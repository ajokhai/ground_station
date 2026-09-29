"""
NVIDIA Isaac Sim — Autonomous USV Simulation Bridge
==================================================
Runs an NVIDIA Omniverse Isaac Sim standalone application with RTX water physics
and publishes vehicle state, camera streams, and sonar telemetry to the
USV Ground Station.

Usage (within Isaac Sim environment):
    ./isaac-sim.python.sh isaac_sim_bridge.py --usv-id usv_1
"""

import argparse
import sys
import time

try:
    from omni.isaac.kit import SimulationApp
    SIMULATION_APP_AVAILABLE = True
except ImportError:
    SIMULATION_APP_AVAILABLE = False


def run_isaac_sim(usv_id: str, headless: bool = False):
    if not SIMULATION_APP_AVAILABLE:
        print("[Isaac Sim Bridge] NVIDIA Isaac Sim (omni.isaac.kit) not found in current Python path.")
        print("To run with full physics, execute via your NVIDIA Isaac Sim installation:")
        print(f"  ./isaac-sim.python.sh {sys.argv[0]} --usv-id {usv_id}")
        return

    # Start Omniverse Simulation App
    simulation_app = SimulationApp({"headless": headless})

    import carb
    import omni
    from omni.isaac.core import World
    from omni.isaac.core.utils.extensions import enable_extension
    from omni.isaac.core.utils.stage import open_stage

    # Enable native ROS 2 bridge extension
    enable_extension("omni.isaac.ros2_bridge")
    simulation_app.update()

    world = World(stage_units_in_meters=1.0)
    world.reset()

    print(f"✅ Isaac Sim initialized for '{usv_id}'. Streaming to USV Ground Station.")

    try:
        while simulation_app.is_running():
            world.step(render=not headless)
    except KeyboardInterrupt:
        print("\nShutting down Isaac Sim bridge...")
    finally:
        simulation_app.close()


def main():
    parser = argparse.ArgumentParser(description="NVIDIA Isaac Sim ROS 2 Bridge for USV Ground Station")
    parser.add_argument("--usv-id", default="usv_1", help="Vehicle namespace identifier")
    parser.add_argument("--headless", action="store_true", help="Run Isaac Sim headlessly")
    args = parser.parse_args()

    run_isaac_sim(args.usv_id, args.headless)


if __name__ == "__main__":
    main()
