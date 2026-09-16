import os

from launch import LaunchDescription
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

    pkg_share = get_package_share_directory(
        "fairino3_v6_moveit2_config"
    )

    moveit_config = (
        MoveItConfigsBuilder(
            "fairino3_v6_robot",
            package_name="fairino3_v6_moveit2_config",
        )
        .robot_description(
            file_path="config/fairino3_v6_robot.real.urdf.xacro"
        )
        .robot_description_semantic(
            file_path="config/fairino3_v6_robot.real.srdf"
        )
        .trajectory_execution(
            file_path="config/moveit_controllers_real.yaml",
            moveit_manage_controllers=False,
        )
        .to_moveit_configs()
    )

    rviz_config = os.path.join(
        pkg_share,
        "config",
        "moveit.rviz",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=[
            "-d",
            rviz_config,
        ],
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": False,
            },
        ],
    )

    return LaunchDescription([
        rviz,
    ])