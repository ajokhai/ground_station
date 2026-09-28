import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ground_station',
            executable='ground_station_node',
            name='ground_station_node',
            output='screen',
            emulate_tty=True
        )
    ])
