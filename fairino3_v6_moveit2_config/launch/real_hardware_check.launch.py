import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory

from fr_control.stage4_config import (
    load_yaml,
    robot_base_xyzw,
    robot_base_xyz,
    workcell_config_path,
)


def generate_launch_description():

    # ============================================================
    # Package paths
    # ============================================================

    pkg_share = get_package_share_directory(
        "fairino3_v6_moveit2_config"
    )

    real_xacro = os.path.join(
        pkg_share,
        "config",
        "fairino3_v6_robot.real.urdf.xacro",
    )

    initial_positions = os.path.join(
        pkg_share,
        "config",
        "initial_positions.yaml",
    )

    controllers_yaml = os.path.join(
        pkg_share,
        "config",
        "ros2_controllers_real.yaml",
    )

    workcell = load_yaml(workcell_config_path())
    install_x, install_y, install_z = robot_base_xyz(workcell)
    install_qx, install_qy, install_qz, install_qw = robot_base_xyzw(
        workcell
    )


    # ============================================================
    # Generate robot_description
    # ============================================================

    robot_description = ParameterValue(
        Command([
            "xacro ",
            real_xacro,
            " initial_positions_file:=",
            initial_positions,
        ]),
        value_type=str,
    )


    # ============================================================
    # world -> base_link
    #
    # IMPORTANT:
    #
    # Same T_world_base as Gazebo / real_bringup:
    # stage4_config.yaml robot.base_pose.
    #
    # It does NOT command any robot motion.
    # ============================================================

    world_to_base_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="world_to_fr3_base",
        output="screen",
        arguments=[
            "--x", str(install_x),
            "--y", str(install_y),
            "--z", str(install_z),

            "--qx", str(install_qx),
            "--qy", str(install_qy),
            "--qz", str(install_qz),
            "--qw", str(install_qw),

            "--frame-id", "world",
            "--child-frame-id", "base_link",
        ],
    )


    # ============================================================
    # Robot State Publisher
    # ============================================================

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": False,
            }
        ],
    )


    # ============================================================
    # ros2_control
    #
    # Hardware still starts UNCONFIGURED.
    # Launching this file alone does not enable/move the robot.
    # ============================================================

    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[
            controllers_yaml,
            {
                "use_sim_time": False,

                "hardware_components_initial_state": {
                    "unconfigured": [
                        "FR3RealSystem",
                    ]
                },
            },
        ],
        remappings=[
            ("~/robot_description", "/robot_description"),
        ],
    )


    return LaunchDescription([
        world_to_base_tf,
        robot_state_publisher,
        controller_manager,
    ])