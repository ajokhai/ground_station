"""
Formation Geometry Calculator for Swarm Coordination.
Calculates coordinate target positions for arbitrary swarm counts and geometries.
"""

import math
from typing import Dict, List, Tuple


def calculate_formation_targets(
    formation_type: str,
    center_x: float,
    center_y: float,
    heading_deg: float,
    spacing: float,
    usv_ids: List[str]
) -> Dict[str, Dict[str, float]]:
    """
    Calculate target coordinates for each USV in the fleet based on the chosen pattern.

    Args:
        formation_type: Formation layout name ('V-Shape', 'Line (Abeam)', 'Column (In-line)', 'Circle', 'Diamond')
        center_x: Formation anchor X coordinate (meters)
        center_y: Formation anchor Y coordinate (meters)
        heading_deg: Formation orientation in degrees (0 = East, 90 = North)
        spacing: Inter-vehicle spacing (meters)
        usv_ids: List of USV identifier strings

    Returns:
        Dictionary mapping usv_id -> {'x': float, 'y': float}
    """
    targets = {}
    n = len(usv_ids)
    if n == 0:
        return targets

    bearing_rad = math.radians(heading_deg)
    # Forward vector (along formation heading)
    fx, fy = math.cos(bearing_rad), math.sin(bearing_rad)
    # Right vector (perpendicular to heading)
    rx, ry = math.sin(bearing_rad), -math.cos(bearing_rad)
    d = spacing

    if formation_type == "V-Shape":
        for i, uid in enumerate(usv_ids):
            if i == 0:
                targets[uid] = {'x': center_x, 'y': center_y}
            else:
                tier = (i + 1) // 2
                side = -1 if (i % 2 == 1) else 1
                targets[uid] = {
                    'x': center_x - tier * d * fx + side * tier * d * rx,
                    'y': center_y - tier * d * fy + side * tier * d * ry,
                }

    elif formation_type == "Line (Abeam)":
        mid = (n - 1) / 2.0
        for i, uid in enumerate(usv_ids):
            off = (i - mid) * d
            targets[uid] = {
                'x': center_x + off * rx,
                'y': center_y + off * ry
            }

    elif formation_type == "Column (In-line)":
        mid = (n - 1) / 2.0
        for i, uid in enumerate(usv_ids):
            off = (mid - i) * d
            targets[uid] = {
                'x': center_x + off * fx,
                'y': center_y + off * fy
            }

    elif formation_type == "Circle":
        radius = max(d, (n * d) / (2.0 * math.pi))
        for i, uid in enumerate(usv_ids):
            angle = bearing_rad + (2.0 * math.pi * i / n)
            targets[uid] = {
                'x': center_x + radius * math.cos(angle),
                'y': center_y + radius * math.sin(angle)
            }

    elif formation_type == "Diamond":
        positions = [(1, 0), (0, -1), (0, 1), (-1, 0)]
        for i, uid in enumerate(usv_ids):
            px, py = positions[i % len(positions)]
            tier = (i // len(positions)) + 1
            targets[uid] = {
                'x': center_x + px * tier * d * fx + py * tier * d * rx,
                'y': center_y + px * tier * d * fy + py * tier * d * ry,
            }
    else:
        # Fallback to clustered around center
        for uid in usv_ids:
            targets[uid] = {'x': center_x, 'y': center_y}

    return targets
