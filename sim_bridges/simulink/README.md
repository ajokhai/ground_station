# MATLAB / Simulink USV Hydrodynamics Connector

This connector provides a high-fidelity **Fossen 6-DOF nonlinear hydrodynamic model** and **Simulink ROS Toolbox** integration for connecting MATLAB/Simulink simulations to the **USV Ground Station**.

---

## Architecture

Simulink interacts directly with the Ground Station over native ROS 2 Humble message blocks:

```
                  ┌──────────────────────────────────────────────┐
                  │              USV Ground Station              │
                  └───────────────┬──────────────▲───────────────┘
                                  │              │
                   /usv_1/cmd_vel │              │ /usv_1/odom
                 (geometry_msgs)  │              │ (nav_msgs)
                                  ▼              │
┌────────────────────────────────────────────────┴───────────────┐
│               Simulink Marine Hydrodynamic Model               │
│                                                                │
│  [Subscribe: cmd_vel]                                          │
│         │                                                      │
│         ▼                                                      │
│  [Thruster Allocation] ──> [Fossen 6-DOF ODE45 Solver]         │
│                                   │                            │
│                                   ▼                            │
│                        [Publish: /usv_1/odom]                  │
└────────────────────────────────────────────────────────────────┘
```

---

## Mathematical Formulation: Fossen (2011) 6-DOF Equations

The vessel state evolves according to:

$$M \dot{\nu} + C(\nu)\nu + D(\nu)\nu + g(\eta) = \tau_{\text{thruster}} + \tau_{\text{env}}$$

$$\dot{\eta} = J(\eta)\nu$$

Where:
- $\eta = [x, y, z, \phi, \theta, \psi]^T$: NED position and Euler orientation angles
- $\nu = [u, v, w, p, q, r]^T$: Body-fixed linear (surge, sway, heave) and angular velocities
- $M = M_{RB} + M_A$: Rigid body mass + hydrodynamic added mass matrix
- $C(\nu) = C_{RB}(\nu) + C_A(\nu)$: Coriolis and centripetal matrix
- $D(\nu) = D_{\text{linear}} + D_{\text{nonlinear}}|\nu|$: Hydrodynamic skin friction and viscous drag
- $g(\eta)$: Hydrostatic restoring forces (buoyancy and gravitational stability)
- $\tau$: Differential twin-thruster surge force and yaw steering moment

---

## Running the Simulation

1. Open MATLAB (R2022b or later with **ROS Toolbox** and **Simulink**).
2. Set your ROS 2 domain in MATLAB:
   ```matlab
   setenv("ROS_DOMAIN_ID", "0");
   ```
3. Run `fossen_6dof_model.m` to start the standalone simulation loop, or open the companion Simulink model.
4. In the Ground Station, switch mode to **`📡 External ROS 2 / Hardware`** to view real-time hydrodynamic trajectories!
