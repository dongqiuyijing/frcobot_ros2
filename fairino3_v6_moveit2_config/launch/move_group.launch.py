from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.actions import SetParameter
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launch_utils import (
    DeclareBooleanLaunchArg,
    add_debuggable_node,
)
import os


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "fairino3_v6_robot",
        package_name="fairino3_v6_moveit2_config",
    ).to_moveit_configs()

    ld = LaunchDescription()
    ld.add_action(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="与 Gazebo 联用时必须为 true，以订阅 /clock。",
        )
    )
    ld.add_action(
        SetParameter(
            name="use_sim_time",
            value=LaunchConfiguration("use_sim_time"),
        )
    )
    ld.add_action(DeclareBooleanLaunchArg("debug", default_value=False))
    ld.add_action(
        DeclareBooleanLaunchArg("allow_trajectory_execution", default_value=True)
    )
    ld.add_action(
        DeclareBooleanLaunchArg(
            "publish_monitored_planning_scene", default_value=True
        )
    )
    ld.add_action(
        DeclareLaunchArgument(
            "capabilities",
            default_value=moveit_config.move_group_capabilities["capabilities"],
        )
    )
    ld.add_action(
        DeclareLaunchArgument(
            "disable_capabilities",
            default_value=moveit_config.move_group_capabilities["disable_capabilities"],
        )
    )

    should_publish = LaunchConfiguration("publish_monitored_planning_scene")
    move_group_configuration = {
        "publish_robot_description_semantic": True,
        "allow_trajectory_execution": LaunchConfiguration(
            "allow_trajectory_execution"
        ),
        "capabilities": ParameterValue(
            LaunchConfiguration("capabilities"), value_type=str
        ),
        "disable_capabilities": ParameterValue(
            LaunchConfiguration("disable_capabilities"), value_type=str
        ),
        "publish_planning_scene": should_publish,
        "publish_geometry_updates": should_publish,
        "publish_state_updates": should_publish,
        "publish_transforms_updates": should_publish,
        "monitor_dynamics": False,
        "use_sim_time": LaunchConfiguration("use_sim_time"),
    }

    add_debuggable_node(
        ld,
        package="moveit_ros_move_group",
        executable="move_group",
        commands_file=str(
            moveit_config.package_path / "launch" / "gdb_settings.gdb"
        ),
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            move_group_configuration,
        ],
        extra_debug_args=["--debug"],
        additional_env={"DISPLAY": os.environ.get("DISPLAY", "")},
    )
    return ld
