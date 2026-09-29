"""
USV Ground Station — Help & User Guide Dialog.
Provides a comprehensive documentation viewer with section navigation,
search filtering, keyboard shortcut tables, and ROS 2 topic references.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QTextBrowser,
    QPushButton, QFrame, QSplitter
)

GUIDE_SECTIONS = {
    "getting_started": {
        "title": "🚀 Getting Started & Overview",
        "keywords": "overview architecture introduction layout coordinates enu wgs84 start",
        "html": """
        <h2>1. Getting Started & System Overview</h2>
        <p>The <b>USV Ground Station</b> is a mission-critical Command &amp; Control (C2) and swarm telemetry platform built for coordinating autonomous Unmanned Surface Vehicle (USV) fleets. It seamlessly integrates a high-performance PyQt5 tactical user interface with <b>ROS 2 Humble</b> (50 Hz spin loop).</p>

        <div style="background: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 12px; margin: 12px 0;">
            <b style="color: #38bdf8;">Core Design Principles:</b>
            <ul>
                <li><b>Strategic C2 vs. Tactical Autonomy:</b> The Ground Station designates fleet formation geometries, swarm corridors, and keep-out boundaries. Individual USVs handle local Guidance, Navigation, &amp; Control (GNC), obstacle avoidance, and thruster dynamics.</li>
                <li><b>Standardized ROS 2 Messaging:</b> Uses industry-standard message types (<code>geometry_msgs</code>, <code>nav_msgs</code>, <code>sensor_msgs</code>) for plug-and-play interoperability with NVIDIA Isaac Sim, MATLAB/Simulink, MuJoCo, and physical onboard Jetson companion computers.</li>
                <li><b>Dual Coordinate System:</b> Bi-directional projection between global <b>WGS84 GPS (Lat/Lon)</b> and local high-precision <b>East-North-Up (ENU)</b> Cartesian meters relative to a configurable Datum Anchor.</li>
            </ul>
        </div>

        <h3>Main User Interface Components:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Component</th>
                <th>Description</th>
                <th>Primary Controls</th>
            </tr>
            <tr>
                <td><b>Header Toolbar</b></td>
                <td>Quick mission execution, map layer switcher, emergency stop, and panel toggles.</td>
                <td>Deploy Swarm, Hold, RTH, ESTOP, Map Style dropdown, Sidebar toggle.</td>
            </tr>
            <tr>
                <td><b>Tactical Radar</b></td>
                <td>2D vector radar HUD displaying vessel glyphs, headings, trails, range rings, and hazards.</td>
                <td>Zoom (Scroll Wheel), Pan (Drag), Floating Toolbar (<code>H</code>, <code>W</code>, <code>P</code>, <code>B</code>, <code>M</code>, <code>R</code>).</td>
            </tr>
            <tr>
                <td><b>Swarm Sidebar</b></td>
                <td>Dual-tab panel for fleet telemetry monitoring, formation tuning, and metocean conditions.</td>
                <td>Formation selector, spacing slider (5m-50m), bearing slider (0°-359°), vessel inspector.</td>
            </tr>
            <tr>
                <td><b>Live Video Feed</b></td>
                <td>First-Person View (FPV) gimbal camera feed with synthetic horizon, compass tape, and VU meter.</td>
                <td>Camera modes (EO/Thermal/NVG), pop-out to external monitor (<code>⤢</code>), canvas drag.</td>
            </tr>
            <tr>
                <td><b>Status Bar</b></td>
                <td>Live system health metrics, link signal strength, cursor GPS/meter coordinates, and uptime.</td>
                <td>Real-time cursor coordinate tracking, active USV RF link dBm, and downlink throughput.</td>
            </tr>
        </table>
        """
    },
    "radar_controls": {
        "title": "🗺️ Tactical Radar & Map Controls",
        "keywords": "radar map navigation zoom pan satellite nautical chart esri open sea map tiles scale bar datum",
        "html": """
        <h2>2. Tactical Radar & Environmental Map Layers</h2>
        <p>The tactical radar provides an interactive, georeferenced maritime operational picture with multiple environmental base layers.</p>

        <h3>Base Map Styles:</h3>
        <ul>
            <li><b>Grid:</b> Dark minimalist tactical grid with 10m concentric range rings and meter ticks.</li>
            <li><b>Tactical:</b> High-contrast cyan reticle HUD with heading ticks and vessel trajectory trails.</li>
            <li><b>Satellite:</b> High-resolution ESRI World Imagery satellite tiles fetched asynchronously with local offline disk caching.</li>
            <li><b>Nautical Chart:</b> ESRI World Ocean base map overlaid with OpenSeaMap marine seamarks, buoys, and navigation aids.</li>
            <li><b>Minimal:</b> Ultra-clean dark slate canvas optimized for low-latency tactical monitoring.</li>
        </ul>

        <h3>Navigation &amp; View Manipulation:</h3>
        <ul>
            <li><b>Pan Canvas:</b> Left-click and drag anywhere on the canvas while in <b>Pan Mode (<code>H</code>)</b>, or middle-click and drag in any mode.</li>
            <li><b>Zoom:</b> Rotate the mouse scroll wheel forward to zoom in and backward to zoom out, or use <kbd>Ctrl</kbd>+<kbd>+</kbd> / <kbd>Ctrl</kbd>+<kbd>-</kbd>.</li>
            <li><b>Recenter Origin:</b> Press the Recenter button (<code>R</code>) on the floating toolbar or press <kbd>Ctrl</kbd>+<kbd>0</kbd> to center on world (0, 0).</li>
            <li><b>Dynamic Scale Bar:</b> Automatically adapts to current zoom level, showing distance in both Metric meters ($m$) and Nautical Miles ($NM$) or Feet ($ft$).</li>
            <li><b>Cursor Coordinate HUD:</b> The bottom-left status bar displays the exact real-time GPS coordinates (Degrees-Minutes-Seconds and Decimal Degrees) and local ENU Cartesian meters under the mouse crosshair.</li>
        </ul>

        <h3>Maritime Operational Areas &amp; GPS Datum:</h3>
        <ul>
            <li><b>15 Global Sea Ports &amp; Testbeds:</b> Quickly teleport the operational theater to pre-configured marine hubs (San Francisco Bay, Port of Rotterdam, Port of Singapore, Sydney Harbour, Portsmouth Naval Base, Strait of Gibraltar, Panama Canal, and open-ocean testbeds) via <b>View &rarr; Maritime Operations Area</b> or <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>D</kbd>.</li>
            <li><b>Interactive GPS Datum Dialog (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>D</kbd>):</b> Search and filter pre-configured ports or enter custom Latitude, Longitude, and Altitude. Automatically re-anchors the local Cartesian origin (0, 0) and re-projects all vessel coordinates and satellite tiles in real time.</li>
            <li><b>Adaptive Zoom Downscaling:</b> High-altitude and coastal zoom levels smoothly downsample tiles to prevent map blanking when zooming out beyond native server resolutions.</li>
        </ul>

        <div style="background: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 10px; margin: 12px 0;">
            <b style="color: #34d399;">💡 Offline Marine Operations:</b> When connected to the internet, viewed satellite and nautical tiles are automatically cached to disk at <code>~/.cache/usv_ground_station/tiles/</code> for disconnected field deployments.
        </div>
        """
    },
    "canvas_toolbar": {
        "title": "🛠️ Figma-Style Canvas Toolbar",
        "keywords": "toolbar floating figma dock tools pan target waypoint boundary polygon hazard ruler measure recenter",
        "html": """
        <h2>3. Figma-Style Floating Canvas Toolbar</h2>
        <p>Docked at the bottom-center of the radar canvas, the floating glassmorphic toolbar provides fast switching between tactical tools with single-key shortcuts.</p>

        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Tool</th>
                <th>Shortcut</th>
                <th>Function &amp; How to Use</th>
            </tr>
            <tr>
                <td><b>✋ Pan</b></td>
                <td><kbd>H</kbd></td>
                <td><b>Safe Default Navigation:</b> Allows clicking and dragging to pan around the map freely without accidentally moving the formation anchor or drawing shapes. Also enables dragging hazard buoys.</td>
            </tr>
            <tr>
                <td><b>🎯 Target</b></td>
                <td><kbd>W</kbd></td>
                <td><b>Formation Anchor Relocation:</b> Left-click anywhere on the radar canvas to designate the new destination center point for the USV swarm. Ghost target markers update immediately.</td>
            </tr>
            <tr>
                <td><b>🛑 Boundary</b></td>
                <td><kbd>P</kbd></td>
                <td><b>Keep-Out Zone Drawing:</b> Click consecutively to place polygon vertices. A live rubber-band preview follows the cursor. Click near the green origin node (within 14px) to snap and close the boundary.</td>
            </tr>
            <tr>
                <td><b>⚠️ Hazard</b></td>
                <td><kbd>B</kbd></td>
                <td><b>Obstacle Buoy Placement:</b> Left-click anywhere on the map to instantly drop a floating navigational hazard buoy (5m radius) with real-time APF deflection.</td>
            </tr>
            <tr>
                <td><b>📏 Ruler</b></td>
                <td><kbd>M</kbd></td>
                <td><b>Tactical Measurement:</b> Click and drag between any two points to measure exact metric distance ($m$/$km$), nautical miles ($NM$), and true compass bearing ($^\\circ T$).</td>
            </tr>
            <tr>
                <td><b>🎯 Recenter</b></td>
                <td><kbd>R</kbd></td>
                <td><b>Instant View Reset:</b> Resets radar pan offset back to the Datum Reference origin (0, 0) with a smooth zoom level.</td>
            </tr>
        </table>
        """
    },
    "swarm_missions": {
        "title": "⛵ Swarm Formation & Mission Control",
        "keywords": "swarm formation missions deploy hold rth estop spacing bearing chevron column line circle diamond",
        "html": """
        <h2>4. Swarm Formation & Mission Execution</h2>
        <p>The USV Ground Station coordinates multi-agent formations with dynamic slot allocation, vessel spacing, and formation bearing.</p>

        <h3>Supported Swarm Formations:</h3>
        <ul>
            <li><b>V-Shape (Chevron):</b> Ideal for forward escort and hydrographic swath coverage. Features lead vehicle at apex with symmetrical angled wings.</li>
            <li><b>Line (Abeam):</b> Vessels advance side-by-side perpendicular to heading, maximizing sensor baseline for bathymetric search.</li>
            <li><b>Column (In-Line):</b> Single-file traversal ideal for navigating narrow channels, harbors, or river corridors.</li>
            <li><b>Circle (Encirclement):</b> Vessels distributed evenly around target center for perimeter defense, cordon, or target loitering.</li>
            <li><b>Diamond:</b> Compact high-maneuverability four-quadrant cluster.</li>
        </ul>

        <h3>Mission Commands:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Command</th>
                <th>Shortcut</th>
                <th>Fleet Action</th>
            </tr>
            <tr>
                <td><b>Deploy Swarm</b></td>
                <td><kbd>Ctrl</kbd>+<kbd>D</kbd></td>
                <td>Commands all active USVs to navigate into their assigned geometric formation slots relative to the target anchor.</td>
            </tr>
            <tr>
                <td><b>Hold Position</b></td>
                <td><kbd>Ctrl</kbd>+<kbd>H</kbd></td>
                <td>Commands all vessels to immediately kill thrust and maintain station-keeping at their current coordinates.</td>
            </tr>
            <tr>
                <td><b>Return to Origin (RTH)</b></td>
                <td><kbd>Ctrl</kbd>+<kbd>R</kbd></td>
                <td>Commands all USVs to navigate back to the mission Datum origin (0, 0) in safe transit configuration.</td>
            </tr>
            <tr>
                <td><b>Emergency Stop (ESTOP)</b></td>
                <td><kbd>Ctrl</kbd>+<kbd>E</kbd></td>
                <td>Safety kill-switch: Immediately halts all kinematic simulation and broadcasts an emergency stop signal over ROS 2.</td>
            </tr>
        </table>

        <h3>Swarm Parameters:</h3>
        <ul>
            <li><b>Vehicle Spacing Slider:</b> Adjusts distance between adjacent vessels from <b>5m</b> (tight tactical) to <b>50m</b> (wide survey).</li>
            <li><b>Formation Bearing Slider:</b> Rotates the entire formation azimuth from <b>0° to 359°</b> true North.</li>
            <li><b>Swarm Size Selector:</b> Scale fleet dynamically from <b>2 up to 8 USVs</b> via the Fleet menu or sidebar dropdown.</li>
        </ul>
        """
    },
    "hazards_geofence": {
        "title": "🛡️ Hazards, APF & Keep-Out Zones",
        "keywords": "hazards obstacles buoys shoals apf potential field geofence keep out boundaries avoidance colregs",
        "html": """
        <h2>5. Marine Hazards, APF Avoidance & Geofencing</h2>
        <p>The Ground Station provides an integrated Artificial Potential Field (APF) obstacle avoidance pipeline, geofence broadcaster, and real-time sensor discovery.</p>

        <h3>Interactive Hazard Management:</h3>
        <ul>
            <li><b>Right-Click Map Context Menu:</b> Right-click anywhere on the radar canvas to place:
                <ul>
                    <li><b>Hazard Buoy (5m radius)</b> — Amber caution halo and red collision buffer.</li>
                    <li><b>Shoal / Shallow Water (8m radius)</b> — Wider navigational hazard.</li>
                    <li><b>Custom Hazard</b> — Specify custom obstacle label and radius in meters.</li>
                </ul>
            </li>
            <li><b>Live Drag &amp; Drop:</b> While in <b>Pan Tool (<code>H</code>)</b> mode, click and drag any hazard circle live across the map to watch USVs autonomously recalculate avoidance vectors in real time!</li>
            <li><b>Right-Click Obstacle Menu:</b> Right-click directly on any obstacle to edit its radius, toggle between Caution/Hazard levels, or delete it.</li>
        </ul>

        <h3>Keep-Out Boundaries &amp; Geofencing:</h3>
        <ul>
            <li><b>Drawing Boundaries:</b> Switch to <b>Boundary Tool (<code>P</code>)</b> and click consecutive points. A rubber-band line previews each segment. Click the initial vertex to close the polygon.</li>
            <li><b>Crimson Warning Zone:</b> Closed boundaries render with translucent red fill (<code>rgba(239, 68, 68, 0.14)</code>), dashed perimeter stroke, and vertex badges.</li>
            <li><b>Autonomous APF Boundary Repulsion:</b> Vessels approaching within 6m of any boundary segment experience smooth repulsive vector deflection, keeping the swarm safely outside forbidden zones.</li>
            <li><b>ROS 2 Geofence Broadcast:</b> Closed boundaries are automatically published to <code>/ground_station/geofence</code> (<code>geometry_msgs/PolygonStamped</code>) with transient local QoS for external autonomous agents.</li>
        </ul>

        <h3>Forward Sensor Cone Discovery:</h3>
        <p>Simulates forward-looking marine LiDAR/Sonar (55° field of view, 26m range). When a USV illuminates an unknown obstacle, it is automatically cataloged in the Ground Station's detected obstacles table with a sensor badge (<code>📡 [USV-1]</code>) and 4m spatial clustering.</p>
        """
    },
    "video_multimonitor": {
        "title": "🎥 Video Feed & Multi-Monitor View",
        "keywords": "video camera fpv gimbal thermal ir night vision hydrophone audio multi monitor detach pop out external display",
        "html": """
        <h2>6. Live FPV Video Feed & Multi-Monitor Support</h2>
        <p>The Ground Station includes a high-fidelity synthetic First-Person View (FPV) camera widget representing the lead vehicle's masthead gimbal.</p>

        <h3>Camera Features &amp; Sensor Modes:</h3>
        <ul>
            <li><b>Daylight (EO):</b> Full-color electro-optical visible spectrum camera with ocean swell rendering.</li>
            <li><b>Thermal IR (White-Hot):</b> High-contrast infrared imagery with warm-body target highlighting and amber HUD reticle.</li>
            <li><b>Night Vision (NVG):</b> Phosphor-green intensified night-vision feed with high sensitivity in low-light conditions.</li>
            <li><b>Telemetry HUD:</b> Artificial horizon, pitch ladder, top heading tape, speed over ground (SOG), and target range.</li>
            <li><b>Marine Hydrophone VU Meter:</b> Live animated decibel meter (-40 dB to 0 dB) simulating underwater acoustic cavitation noise and audio mute toggle.</li>
        </ul>

        <h3>Canvas Dragging &amp; Multi-Monitor Pop-Out:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Action</th>
                <th>Control</th>
                <th>Description</th>
            </tr>
            <tr>
                <td><b>Reposition on Canvas</b></td>
                <td>Drag <b>⠿ Header Bar</b></td>
                <td>Click and drag the tactical grip handle (<code>⠿</code>) to position the video PiP anywhere over the radar canvas. Clamped within screen bounds.</td>
            </tr>
            <tr>
                <td><b>Pop-Out / Detach</b></td>
                <td>Click <b>⤢ Button</b></td>
                <td>Detaches the video feed into an independent top-level OS window. Drag this window onto a secondary monitor or external display!</td>
            </tr>
            <tr>
                <td><b>Re-Dock to Canvas</b></td>
                <td>Click <b>↙ Button</b></td>
                <td>Instantly docks the detached video feed back into the radar canvas at its previous position.</td>
            </tr>
            <tr>
                <td><b>Toggle Expanded View</b></td>
                <td>Double-click Header or <b>⇄</b></td>
                <td>Expands the video feed to fill the entire radar canvas, or restores back to compact floating PiP.</td>
            </tr>
        </table>
        """
    },
    "shortcuts": {
        "title": "⌨️ Keyboard & Mouse Shortcuts",
        "keywords": "shortcuts keys keyboard hotkeys controls cheatsheet",
        "html": """
        <h2>7. Keyboard & Mouse Shortcuts Reference</h2>
        <p>Master these shortcuts for rapid tactical mission control during operations:</p>

        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Shortcut</th>
                <th>Context</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><kbd>H</kbd></td>
                <td>Canvas Toolbar</td>
                <td>Switch to <b>Pan Tool</b> (safe drag navigation, buoy manipulation)</td>
            </tr>
            <tr>
                <td><kbd>W</kbd></td>
                <td>Canvas Toolbar</td>
                <td>Switch to <b>Target Tool</b> (set swarm waypoint)</td>
            </tr>
            <tr>
                <td><kbd>P</kbd></td>
                <td>Canvas Toolbar</td>
                <td>Switch to <b>Boundary Tool</b> (draw keep-out geofence)</td>
            </tr>
            <tr>
                <td><kbd>B</kbd></td>
                <td>Canvas Toolbar</td>
                <td>Switch to <b>Hazard Buoy Tool</b> (drop obstacle)</td>
            </tr>
            <tr>
                <td><kbd>M</kbd></td>
                <td>Canvas Toolbar</td>
                <td>Switch to <b>Ruler Tool</b> (measure distance and bearing)</td>
            </tr>
            <tr>
                <td><kbd>R</kbd></td>
                <td>Canvas Toolbar</td>
                <td><b>Recenter View</b> on Datum origin (0, 0)</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>D</kbd></td>
                <td>Global</td>
                <td><b>Deploy Swarm Formation</b></td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>H</kbd></td>
                <td>Global</td>
                <td><b>Hold Position</b> (kill thrust &amp; station keep)</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>R</kbd></td>
                <td>Global</td>
                <td><b>Return to Origin (RTH)</b></td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>E</kbd></td>
                <td>Global</td>
                <td><b>Emergency Stop (ESTOP)</b></td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>1</kbd></td>
                <td>Global</td>
                <td>Toggle Swarm Sidebar visibility</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>V</kbd></td>
                <td>Global</td>
                <td>Toggle Live Video Feed visibility</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>`</kbd></td>
                <td>Global</td>
                <td>Toggle Telemetry &amp; Event Log Console</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>+</kbd> / <kbd>-</kbd></td>
                <td>Radar</td>
                <td>Zoom In / Zoom Out</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>0</kbd></td>
                <td>Radar</td>
                <td>Reset view zoom and pan to origin</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>D</kbd></td>
                <td>Global</td>
                <td>Open <b>Maritime Operations Area &amp; GPS Datum</b> picker dialog</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd></td>
                <td>Global</td>
                <td>Open <b>Fleet Analytics &amp; Diagnostic Telemetry</b> dialog</td>
            </tr>
            <tr>
                <td><kbd>Ctrl</kbd>+<kbd>/</kbd></td>
                <td>Global</td>
                <td>Open Quick Shortcuts Cheatsheet</td>
            </tr>
            <tr>
                <td><kbd>W</kbd> / <kbd>A</kbd> / <kbd>S</kbd> / <kbd>D</kbd> or <kbd>&uarr;</kbd> / <kbd>&larr;</kbd> / <kbd>&darr;</kbd> / <kbd>&rarr;</kbd></td>
                <td>Manual Drive</td>
                <td><b>Direct Teleoperation:</b> Throttle forward/reverse and rudder steering when a USV is selected (publishes <code>/usv_{id}/cmd_vel</code>)</td>
            </tr>
            <tr>
                <td><kbd>Space</kbd></td>
                <td>Manual Drive</td>
                <td>Zero-thrust dynamic brake during manual teleoperation</td>
            </tr>
            <tr>
                <td><kbd>F1</kbd></td>
                <td>Global</td>
                <td>Open this <b>User Guide &amp; Reference</b> dialog</td>
            </tr>
        </table>
        """
    },
    "ros2_architecture": {
        "title": "🌐 ROS 2 Architecture & Topics",
        "keywords": "ros ros2 topics downlink uplink odom target_pose autonomy_mode geofence formation_cmd telemetry",
        "html": """
        <h2>8. Standard ROS 2 Topic Architecture</h2>
        <p>The Ground Station follows a clean separation between high-level fleet directives and individual vehicle telemetries using standard ROS 2 Humble packages.</p>

        <h3>Ground Station Broadcasts (GCS &rarr; Fleet):</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Topic</th>
                <th>Message Type</th>
                <th>Description</th>
            </tr>
            <tr>
                <td><code>/ground_station/formation_cmd</code></td>
                <td><code>std_msgs/msg/String</code></td>
                <td>JSON payload detailing target formation type, center coordinates, vehicle spacing, and bearing.</td>
            </tr>
            <tr>
                <td><code>/ground_station/geofence</code></td>
                <td><code>geometry_msgs/msg/PolygonStamped</code></td>
                <td>Keep-out boundary polygon vertices published with transient local durability QoS.</td>
            </tr>
            <tr>
                <td><code>/ground_station/emergency_stop</code></td>
                <td><code>std_msgs/msg/Bool</code></td>
                <td>Fleet-wide emergency kill signal.</td>
            </tr>
            <tr>
                <td><code>/ground_station/heartbeat</code></td>
                <td><code>std_msgs/msg/String</code></td>
                <td>1 Hz health heartbeat with timestamp and active vessel count.</td>
            </tr>
        </table>

        <h3>Per-Agent Downlinks (GCS &rarr; USV):</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Topic</th>
                <th>Message Type</th>
                <th>Description</th>
            </tr>
            <tr>
                <td><code>/usv_{id}/target_pose</code></td>
                <td><code>geometry_msgs/msg/PoseStamped</code></td>
                <td>Assigned target slot position $(x, y)$ in ENU meters and orientation quaternion published at 5 Hz.</td>
            </tr>
            <tr>
                <td><code>/usv_{id}/autonomy_mode</code></td>
                <td><code>std_msgs/msg/String</code></td>
                <td>Directives: <code>FORMATION</code>, <code>TRANSIT</code>, <code>HOLD</code>, <code>RTH</code>, <code>MANUAL</code>, <code>AVOIDING</code>.</td>
            </tr>
            <tr>
                <td><code>/usv_{id}/cmd_vel</code></td>
                <td><code>geometry_msgs/msg/Twist</code></td>
                <td>Direct manual teleoperation velocity commands when manual drive is engaged.</td>
            </tr>
        </table>

        <h3>Per-Agent Uplinks (USV &rarr; GCS):</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border-color: #27272a; width: 100%;">
            <tr style="background: #121216; color: #38bdf8;">
                <th>Topic</th>
                <th>Message Type</th>
                <th>Description</th>
            </tr>
            <tr>
                <td><code>/usv_{id}/odom</code></td>
                <td><code>nav_msgs/msg/Odometry</code></td>
                <td>True vessel kinematic state (position, velocity, and orientation).</td>
            </tr>
            <tr>
                <td><code>/usv_{id}/battery</code></td>
                <td><code>sensor_msgs/msg/BatteryState</code></td>
                <td>Battery percentage, voltage, and power consumption metrics.</td>
            </tr>
            <tr>
                <td><code>/usv_{id}/sensors/sonar</code></td>
                <td><code>sensor_msgs/msg/Range</code></td>
                <td>Forward acoustic rangefinder distance soundings.</td>
            </tr>
            <tr>
                <td><code>/usv_{id}/camera/image_raw/compressed</code></td>
                <td><code>sensor_msgs/msg/CompressedImage</code></td>
                <td>Real-time JPEG compressed FPV / gimbal camera video feed.</td>
            </tr>
            <tr>
                <td><code>/ground_station/detected_obstacles</code></td>
                <td><code>visualization_msgs/msg/MarkerArray</code></td>
                <td>Aggregated obstacle discoveries from onboard LiDAR/vision perception nodes.</td>
            </tr>
        </table>

        <div style="background: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 12px; margin: 12px 0;">
            <b style="color: #38bdf8;">Simulator &amp; Hardware Compatibility:</b>
            <p style="margin: 4px 0 0 0;">This topic schema allows seamless connection with NVIDIA Isaac Sim (RTX water &amp; camera sensors), MATLAB / Simulink (Fossen 6-DOF hydrodynamic models), MuJoCo physics, or physical companion computers over CycloneDDS / Zenoh bridges.</p>
        </div>
        """
    },
    "hardware_sim_bridge": {
        "title": "📡 Real USV & Simulator Integration",
        "keywords": "hardware real usv external simulator isaac sim gazebo mujoco simulink jetson onboarding bridge discovery cmd_vel odom dds",
        "html": """
        <h2>9. Real USV &amp; External Simulator Integration Flow</h2>
        <p>The USV Ground Station is engineered to bridge smoothly between rapid desktop testing and physical maritime sea trials with zero code modifications.</p>

        <div style="background: #18181b; border: 1px solid #27272a; border-radius: 6px; padding: 12px; margin: 12px 0;">
            <b style="color: #38bdf8;">Dual Operation Modes:</b>
            <ul>
                <li><b>🎮 Standalone Simulation:</b> Built-in 2D kinematic engine and APF steering for zero-hardware desktop testing. USV movements are computed locally.</li>
                <li><b>📡 External ROS 2 / Hardware:</b> Suspends internal Euler kinematics. Ingests true physical/simulated odometry, battery status, sonar depth, and camera video from external nodes while continuing to transmit formation downlinks and teleop commands at 50 Hz.</li>
            </ul>
        </div>

        <h3>Step-by-Step Onboarding Flow:</h3>
        <ol style="line-height: 1.8;">
            <li><b>Network &amp; DDS Domain Alignment:</b> Ensure the Ground Station machine and your companion computer (NVIDIA Jetson, Raspberry Pi, or external simulator host) are on the same local subnet, Wi-Fi, mesh radio, or VPN tunnel. Verify that both share the same ROS 2 Domain ID:
                <pre style="background: #121216; padding: 8px; border-radius: 4px; border: 1px solid #27272a; color: #34d399;">export ROS_DOMAIN_ID=0  # default, or your fleet domain ID</pre>
            </li>
            <li><b>Switch Operation Mode:</b> In the main toolbar, switch the mode dropdown from <code>🎮 Standalone Simulation</code> to <code>📡 External ROS 2 / Hardware</code>. A cyan <code>📡 EXTERNAL ROS 2</code> indicator confirms ingestion mode.</li>
            <li><b>Launch Vehicle Telemetry Publishers:</b> Onboard the physical USV or within Isaac Sim / Gazebo / MuJoCo, launch a node publishing to standard vehicle namespaces:
                <ul>
                    <li><code>/usv_1/odom</code> (<code>nav_msgs/msg/Odometry</code>) — Kinematic state (position in ENU meters, velocity, orientation quaternion).</li>
                    <li><code>/usv_1/battery</code> (<code>sensor_msgs/msg/BatteryState</code>) — State of charge percentage (0.0 to 1.0) and bus voltage.</li>
                    <li><code>/usv_1/sensors/sonar</code> (<code>sensor_msgs/msg/Range</code>) — Obstacle clearance or water depth soundings.</li>
                    <li><code>/usv_1/camera/image_raw/compressed</code> (<code>sensor_msgs/msg/CompressedImage</code>) — Real-time JPEG FPV camera stream.</li>
                </ul>
            </li>
            <li><b>Zero-Config Dynamic Auto-Discovery:</b> The Ground Station's background discovery daemon automatically scans the ROS 2 topic graph at 1.5 Hz. As soon as <code>/usv_{id}/odom</code> is detected, the vehicle is automatically registered:
                <ul>
                    <li>A live telemetry card is created in the Swarm Fleet sidebar panel.</li>
                    <li>A vessel glyph appears immediately at its real GPS/ENU coordinates on the tactical radar.</li>
                    <li>Downlink command publishers (<code>/usv_{id}/target_pose</code>, <code>/usv_{id}/autonomy_mode</code>, <code>/usv_{id}/cmd_vel</code>) are bound automatically.</li>
                </ul>
            </li>
            <li><b>Command &amp; Teleoperation:</b>
                <ul>
                    <li><b>Formation Directives:</b> Click <b>Deploy Swarm (<kbd>Ctrl+D</kbd>)</b> to broadcast target slot coordinates to <code>/usv_{id}/target_pose</code>.</li>
                    <li><b>Manual Keyboard Drive:</b> Select the USV and use <kbd>W</kbd>/<kbd>A</kbd>/<kbd>S</kbd>/<kbd>D</kbd> or Arrow Keys. The Ground Station publishes <code>geometry_msgs/Twist</code> directly to <code>/usv_{id}/cmd_vel</code>. Releasing keys immediately transmits an automatic zero-velocity safety stop.</li>
                    <li><b>Emergency Stop (<kbd>Ctrl+E</kbd>):</b> Broadcasts a high-priority kill command to <code>/ground_station/emergency_stop</code> and commands zero thrust to all active USVs.</li>
                </ul>
            </li>
        </ol>

        <h3>Verification with ROS 2 CLI:</h3>
        <p>You can quickly verify that external telemetry is reaching the station by echoing topics from any terminal:</p>
        <pre style="background: #121216; padding: 8px; border-radius: 4px; border: 1px solid #27272a; color: #a1a1aa;">
# Check active USV namespaces
ros2 topic list | grep usv_

# Echo target formation downlinks sent from Ground Station to USV-1
ros2 topic echo /usv_1/target_pose

# Echo manual teleoperation drive commands
ros2 topic echo /usv_1/cmd_vel
        </pre>
        """
    }
}


class HelpGuideDialog(QDialog):
    """Modern dark-themed comprehensive user guide and help dialog."""

    def __init__(self, parent=None, initial_section="getting_started"):
        super().__init__(parent)
        self.setWindowTitle("USV Ground Station — User Guide & Reference")
        self.resize(1020, 680)
        self.setMinimumSize(780, 500)
        self.setStyleSheet("""
            QDialog {
                background: #09090b;
                color: #fafafa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ─── Top Header Bar ───
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        dlg_title = QLabel("USV Ground Station — User Guide & Reference")
        dlg_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        dlg_subtitle = QLabel("Comprehensive operation manual, tactical controls, keyboard shortcuts, and ROS 2 specs")
        dlg_subtitle.setStyleSheet("font-size: 11px; color: #71717a;")
        title_col.addWidget(dlg_title)
        title_col.addWidget(dlg_subtitle)
        header_bar.addLayout(title_col)

        header_bar.addStretch()

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search guide (e.g. geofence, APF, shortcuts)...")
        self.search_box.setFixedWidth(260)
        self.search_box.setFixedHeight(28)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                padding: 0 8px;
                color: #fafafa;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        self.search_box.textChanged.connect(self._on_search_text_changed)
        header_bar.addWidget(self.search_box)

        layout.addLayout(header_bar)

        # ─── Splitter Body ───
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #27272a;
                width: 1px;
            }
        """)

        # Left Navigation List
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(240)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: #121216;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 4px;
                color: #a1a1aa;
                font-size: 12px;
                font-weight: 500;
            }
            QListWidget::item {
                padding: 10px 10px;
                border-radius: 5px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background: #1c1c22;
                color: #e4e4e7;
            }
            QListWidget::item:selected {
                background: #27272a;
                color: #38bdf8;
                font-weight: 700;
            }
        """)

        for key, sec in GUIDE_SECTIONS.items():
            item = QListWidgetItem(sec["title"])
            item.setData(Qt.UserRole, key)
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_section_selected)
        splitter.addWidget(self.nav_list)

        # Right Content Browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setStyleSheet("""
            QTextBrowser {
                background: #09090b;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 18px;
                color: #d4d4d8;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        splitter.addWidget(self.content_browser)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

        # ─── Bottom Footer ───
        footer = QHBoxLayout()
        ver_lbl = QLabel("Version 2.4.0 • ROS 2 Humble & PyQt5 • Multi-Agent C2 Framework")
        ver_lbl.setStyleSheet("font-size: 10px; color: #52525b;")
        footer.addWidget(ver_lbl)

        footer.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedSize(80, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                color: #e4e4e7;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #27272a;
                border-color: #38bdf8;
                color: #38bdf8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

        # Select initial section
        self._select_section(initial_section)

    def _select_section(self, section_key: str):
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            if item.data(Qt.UserRole) == section_key:
                self.nav_list.setCurrentRow(i)
                break
        else:
            if self.nav_list.count() > 0:
                self.nav_list.setCurrentRow(0)

    def _on_section_selected(self, row: int):
        item = self.nav_list.item(row)
        if not item:
            return
        key = item.data(Qt.UserRole)
        section = GUIDE_SECTIONS.get(key)
        if section:
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
                        color: #d4d4d8;
                        background: #09090b;
                        line-height: 1.6;
                    }}
                    h2 {{
                        color: #38bdf8;
                        font-size: 18px;
                        margin-top: 0;
                        padding-bottom: 6px;
                        border-bottom: 1px solid #27272a;
                    }}
                    h3 {{
                        color: #fafafa;
                        font-size: 14px;
                        margin-top: 18px;
                        margin-bottom: 8px;
                    }}
                    p, li {{
                        color: #d4d4d8;
                        font-size: 12px;
                    }}
                    code {{
                        background: #18181b;
                        color: #38bdf8;
                        padding: 2px 5px;
                        border-radius: 4px;
                        font-family: Menlo, Monaco, monospace;
                        font-size: 11px;
                    }}
                    kbd {{
                        background: #27272a;
                        color: #fafafa;
                        padding: 2px 6px;
                        border-radius: 4px;
                        border: 1px solid #3f3f46;
                        font-family: Menlo, Monaco, monospace;
                        font-size: 10px;
                        font-weight: bold;
                    }}
                    table {{
                        margin-top: 10px;
                        margin-bottom: 14px;
                        border-collapse: collapse;
                    }}
                    th {{
                        background: #121216;
                        color: #38bdf8;
                        text-align: left;
                        font-weight: 600;
                        font-size: 11px;
                        padding: 8px;
                        border: 1px solid #27272a;
                    }}
                    td {{
                        padding: 8px;
                        border: 1px solid #27272a;
                        font-size: 11px;
                    }}
                    tr:nth-child(even) {{
                        background: #0e0e12;
                    }}
                </style>
            </head>
            <body>
                {section["html"]}
            </body>
            </html>
            """
            self.content_browser.setHtml(html_content)

    def _on_search_text_changed(self, query: str):
        query = query.strip().lower()
        if not query:
            for i in range(self.nav_list.count()):
                self.nav_list.item(i).setHidden(False)
            return

        first_match = -1
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            key = item.data(Qt.UserRole)
            sec = GUIDE_SECTIONS.get(key, {})
            text_to_search = f"{sec.get('title', '')} {sec.get('keywords', '')} {sec.get('html', '')}".lower()
            matches = query in text_to_search
            item.setHidden(not matches)
            if matches and first_match == -1:
                first_match = i

        if first_match != -1:
            self.nav_list.setCurrentRow(first_match)
