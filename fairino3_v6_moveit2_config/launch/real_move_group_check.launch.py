from launch import LaunchDescription
from launch_ros.actions import Node

from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

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
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": False,

                # 当前阶段只验证 MoveIt 规划链。
                # 禁止执行真实轨迹。
                "allow_trajectory_execution": False,
            },
        ],
    )

    return LaunchDescription([
        move_group,
    ])