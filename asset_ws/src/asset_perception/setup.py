from setuptools import find_packages, setup
import os
from glob import glob

package_name = "asset_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "rviz"), glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="SaladinIART",
    maintainer_email="asset-vision@users.noreply.github.com",
    description="Asset-Vision ROS2 perception nodes",
    license="MIT",
    entry_points={
        "console_scripts": [
            "camera_node    = asset_perception.camera_node:main",
            "perception_node = asset_perception.perception_node:main",
            "manager_node   = asset_perception.manager_node:main",
        ],
    },
)
