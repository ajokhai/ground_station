%% Fossen 6-DOF Marine Hydrodynamics Simulation Bridge for ROS 2
% USV Ground Station Integration
%
% Implements Thor I. Fossen's standard nonlinear marine craft equations
% of motion for an autonomous catamaran surface vessel:
%   M * nu_dot + C(nu)*nu + D(nu)*nu + g(eta) = tau
%   eta_dot = J(eta) * nu

function fossen_6dof_model(usv_id)
    if nargin < 1
        usv_id = 'usv_1';
    end

    fprintf('=== Initializing Fossen 6-DOF Hydrodynamic Model for %s ===\n', usv_id);

    %% 1. Vessel Physical & Hydrodynamic Parameters (3m Catamaran)
    m     = 180.0;           % Mass [kg]
    Iz    = 85.0;            % Yaw moment of inertia [kg*m^2]
    L     = 3.2;             % Length [m]
    B     = 1.4;             % Beam width [m]

    % Hydrodynamic Added Mass Coefficients (SNAME notation)
    X_udot = -25.0;          % Surge added mass [kg]
    Y_vdot = -95.0;          % Sway added mass [kg]
    N_rdot = -45.0;          % Yaw added inertia [kg*m^2]

    % Total Inertia Matrix (Rigid Body + Added Mass)
    M = diag([m - X_udot, m - Y_vdot, Iz - N_rdot]);
    M_inv = inv(M);

    % Hydrodynamic Damping Parameters (Linear + Quadratic Drag)
    X_u    = 45.0;   X_uu  = 35.0;   % Surge damping
    Y_v    = 80.0;   Y_vv  = 120.0;  % Sway damping
    N_r    = 50.0;   N_rr  = 40.0;   % Yaw damping

    %% 2. Kinematic State Variables
    % eta = [x (Easting), y (Northing), psi (Heading rad)]
    eta = [0.0; 0.0; pi/2];
    % nu  = [u (Surge m/s), v (Sway m/s), r (Yaw rate rad/s)]
    nu  = [0.0; 0.0; 0.0];

    % Control inputs from /cmd_vel: [surge_force (N), yaw_moment (N*m)]
    tau = [0.0; 0.0; 0.0];
    battery_soc = 98.5;

    %% 3. ROS 2 Initialization (MATLAB ROS Toolbox)
    try
        gcs_node = ros2node(sprintf('%s_simulink_bridge', usv_id));
        odom_pub = ros2publisher(gcs_node, sprintf('/%s/odom', usv_id), 'nav_msgs/Odometry');
        batt_pub = ros2publisher(gcs_node, sprintf('/%s/battery', usv_id), 'sensor_msgs/BatteryState');

        cmd_sub = ros2subscriber(gcs_node, sprintf('/%s/cmd_vel', usv_id), 'geometry_msgs/Twist', ...
            @(msg) on_cmd_vel(msg));
        fprintf('Connected to ROS 2 topic graph. Ingesting commands and streaming telemetry.\n');
    catch ME
        warning('ROS Toolbox not detected or ROS 2 daemon unreachable: %s', ME.message);
        fprintf('Proceeding in dry-run simulation mode.\n');
        gcs_node = [];
    end

    %% 4. Main Simulation Loop (50 Hz Integration)
    dt = 0.02; % 50 Hz
    t_start = tic;

    fprintf('Simulation active. Press Ctrl+C in MATLAB to stop.\n');
    while true
        loop_start = tic;

        u = nu(1); v = nu(2); r = nu(3);
        psi = eta(3);

        % Coriolis & Centripetal Matrix C(nu)
        c13 = -(m - Y_vdot) * v;
        c23 = (m - X_udot) * u;
        C = [  0,    0,   c13;
               0,    0,   c23;
             -c13, -c23,   0 ];

        % Nonlinear Damping Matrix D(nu)
        D = [ X_u + X_uu*abs(u),          0,                   0;
                     0,           Y_v + Y_vv*abs(v),           0;
                     0,                   0,           N_r + N_rr*abs(r) ];

        % Fossen Dynamic Acceleration: nu_dot = M \ (tau - C*nu - D*nu)
        nu_dot = M_inv * (tau - C * nu - D * nu);

        % Velocity update (Euler forward step)
        nu = nu + nu_dot * dt;

        % Kinematic Transformation Matrix J(eta)
        R = [ cos(psi), -sin(psi), 0;
              sin(psi),  cos(psi), 0;
                 0,         0,     1 ];

        % World position update
        eta_dot = R * nu;
        eta = eta + eta_dot * dt;
        eta(3) = mod(eta(3), 2*pi); % Wrap heading [0, 2*pi)

        % Battery discharge
        battery_soc = max(5.0, battery_soc - 0.0002);

        % Dispatch ROS 2 Odometry
        if ~isempty(gcs_node)
            odom_msg = ros2message(odom_pub);
            odom_msg.header.stamp = rostime('now');
            odom_msg.header.frame_id = 'world';
            odom_msg.child_frame_id = sprintf('%s_base_link', usv_id);

            odom_msg.pose.pose.position.x = eta(1);
            odom_msg.pose.pose.position.y = eta(2);
            odom_msg.pose.pose.position.z = 0.0;

            % Orientation quaternion (Planar yaw)
            half_yaw = eta(3) * 0.5;
            odom_msg.pose.pose.orientation.z = sin(half_yaw);
            odom_msg.pose.pose.orientation.w = cos(half_yaw);

            odom_msg.twist.twist.linear.x = nu(1);
            odom_msg.twist.twist.linear.y = nu(2);
            odom_msg.twist.twist.angular.z = nu(3);

            send(odom_pub, odom_msg);
        end

        % Maintain 50 Hz loop pacing
        elapsed = toc(loop_start);
        pause(max(0.001, dt - elapsed));
    end

    %% Callback: Process /cmd_vel into thruster forces
    function on_cmd_vel(twist_msg)
        % Map linear surge velocity to thrust force (N)
        cmd_surge = twist_msg.linear.x;
        % Map angular yaw velocity to steering moment (N*m)
        cmd_yaw   = twist_msg.angular.z;

        tau(1) = cmd_surge * 80.0;   % ~350 N peak thrust
        tau(3) = cmd_yaw * 45.0;     % Differential steering moment
    end
end
