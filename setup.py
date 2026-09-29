import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'ground_station'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chenhangwei',
    maintainer_email='chenhangwei77777@hotmail.com',
    description='A ground station control package for managing and coordinating unmanned surface vehicle (USV) swarm formations.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'ground_station_node = ground_station.ground_station_node:main',
            'usv_agent_node = ground_station.nodes.usv_agent_node:main',
            'usv_swarm_sim = usv_sdk.cli:main',
        ],
    },
)
