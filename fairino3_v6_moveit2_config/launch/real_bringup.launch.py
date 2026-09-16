import os

from launch import LaunchDescription
from launch.actions import (
    RegisterEventHandler,
    LogInfo,
    EmitEvent,
)
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.events import Shutdown

from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue

from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

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

    ros2_controllers_yaml = os.path.join(
        pkg_share,
        "config",
        "ros2_controllers_real.yaml",
    )

    arm_controller_yaml = os.path.join(
        pkg_share,
        "config",
        "fairino3_controller_real.yaml",
    )

    workcell_yaml = workcell_config_path()

    rviz_config = os.path.join(
        pkg_share,
        "config",
        "moveit.rviz",
    )


    # ============================================================
    # world -> base_link  =  T_world_base
    #
    # Shared with Gazebo: fr_control/config/stage4_config.yaml
    # robot.base_pose
    #
    # Changing this TF does NOT command robot motion.
    # ============================================================

    workcell_config = load_yaml(workcell_yaml)
    install_x, install_y, install_z = robot_base_xyz(workcell_config)
    install_qx, install_qy, install_qz, install_qw = robot_base_xyzw(
        workcell_config
    )


    # ============================================================
    # REAL robot_description
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
    # Physical installation pose of the complete FR3 robot.
    #
    # This transform itself does NOT command robot motion.
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
    # Keep FR3RealSystem initially UNCONFIGURED.
    #
    # hardware_spawner below will perform:
    #
    # unconfigured
    #      ↓
    # inactive
    #      ↓
    # active
    #
    # This eventually calls our FairinoHardwareInterface
    # on_activate():
    #
    # RPC
    # current joint synchronization
    # RobotEnable(1)
    # ServoMoveStart()
    # ============================================================

    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[
            ros2_controllers_yaml,
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


    # ============================================================
    # Activate REAL FR3 hardware
    #
    # Do not start hardware_spawner until FR3RealSystem is listed
    # by list_hardware_components. hardware_spawner exit code 0
    # is NOT proof of ACTIVE (it can exit 0 when the component
    # is not loaded). A second wait verifies state.label=active.
    # ============================================================

    wait_hardware_present = Node(
        package="fairino3_v6_moveit2_config",
        executable="wait_hardware_component",
        name="wait_fr3_hardware_present",
        output="screen",
        arguments=[
            "--component",
            "FR3RealSystem",
            "--state",
            "present",
            "--timeout",
            "30",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    hardware_spawner = Node(
        package="controller_manager",
        executable="hardware_spawner",
        name="fr3_hardware_spawner",
        output="screen",
        arguments=[
            "FR3RealSystem",
            "--activate",
            "-c",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
    )

    wait_hardware_active = Node(
        package="fairino3_v6_moveit2_config",
        executable="wait_hardware_component",
        name="wait_fr3_hardware_active",
        output="screen",
        arguments=[
            "--component",
            "FR3RealSystem",
            "--state",
            "active",
            "--timeout",
            "30",
            "--controller-manager",
            "/controller_manager",
        ],
    )


    # ============================================================
    # Joint State Broadcaster
    #
    # Real FR3
    #   ↓
    # FairinoHardwareInterface::read()
    #   ↓
    # /joint_states
    # ============================================================

    joint_state_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "joint_state_broadcaster",
            "-c",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
    )


    # ============================================================
    # FR3 trajectory controller
    #
    # MoveIt
    #   ↓
    # FollowJointTrajectory
    #   ↓
    # fairino3_controller
    #   ↓
    # j1 ~ j6 position interfaces
    # ============================================================

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "fairino3_controller",

            "-c",
            "/controller_manager",

            "-t",
            "joint_trajectory_controller/JointTrajectoryController",

            "-p",
            arm_controller_yaml,

            "--controller-manager-timeout",
            "30",
        ],
    )


    # ============================================================
    # MoveIt REAL configuration
    # ============================================================

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


    # ============================================================
    # Move Group
    #
    # Trajectory execution is ENABLED.
    #
    # Therefore after bringup:
    #
    # RViz Execute / programmatic MoveIt execution
    # CAN move the real FR3.
    # ============================================================

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "use_sim_time": False,
                "allow_trajectory_execution": True,
            },
        ],
    )


    # ============================================================
    # RViz
    # ============================================================

    rviz = Node(
        package="rviz2",
        executable="rviz2",
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


    # Fixed workcell collision geometry (column / table).
    # Same YAML as Gazebo and as T_world_base above.
    workcell_scene_loader = Node(
        package="fr_control",
        executable="workcell_scene_loader",
        name="workcell_scene_loader",
        output="screen",
        parameters=[
            {
                "use_sim_time": False,
                "config_file": workcell_yaml,
                "include_object": False,
            }
        ],
    )


    # ============================================================
    # Sequential startup callbacks
    #
    # controller_manager
    #    ↓
    # wait FR3RealSystem PRESENT  (list_hardware_components)
    #    ↓
    # hardware_spawner --activate
    #    ↓
    # wait FR3RealSystem ACTIVE   (state.label == active)
    #    ↓
    # JointStateBroadcaster
    #    ↓
    # Trajectory Controller
    #    ↓
    # MoveIt + RViz + workcell_scene_loader
    #
    # hardware_spawner returncode==0 is not treated as ACTIVE.
    # If one critical stage fails, stop bringup.
    # ============================================================

    def after_hardware_present(event, context):

        if event.returncode != 0:
            return [
                LogInfo(
                    msg="[REAL BRINGUP] FR3RealSystem was not registered."
                ),
                EmitEvent(
                    event=Shutdown(
                        reason="FR3RealSystem not present in ResourceManager"
                    )
                ),
            ]

        return [
            LogInfo(
                msg="[REAL BRINGUP] FR3RealSystem registered."
            ),
            LogInfo(
                msg="[REAL BRINGUP] Activating FR3RealSystem..."
            ),
            hardware_spawner,
        ]


    def after_hardware_spawner(event, context):

        if event.returncode != 0:
            return [
                LogInfo(
                    msg="[REAL BRINGUP] FR3 hardware_spawner FAILED."
                ),
                EmitEvent(
                    event=Shutdown(
                        reason="FR3 hardware_spawner failed"
                    )
                ),
            ]

        return [
            LogInfo(
                msg="[REAL BRINGUP] Verifying FR3RealSystem ACTIVE..."
            ),
            wait_hardware_active,
        ]


    def after_hardware_active(event, context):

        if event.returncode != 0:
            return [
                LogInfo(
                    msg="[REAL BRINGUP] FR3RealSystem ACTIVE verification FAILED."
                ),
                EmitEvent(
                    event=Shutdown(
                        reason="FR3RealSystem is not active"
                    )
                ),
            ]

        return [
            LogInfo(
                msg="[REAL BRINGUP] FR3RealSystem ACTIVE verified."
            ),
            LogInfo(
                msg="[REAL BRINGUP] Starting JointStateBroadcaster..."
            ),
            joint_state_spawner,
        ]


    def after_joint_state(event, context):

        if event.returncode != 0:
            return [
                LogInfo(
                    msg="[REAL BRINGUP] JointStateBroadcaster FAILED."
                ),
                EmitEvent(
                    event=Shutdown(
                        reason="JointStateBroadcaster failed"
                    )
                ),
            ]

        return [
            LogInfo(
                msg="[REAL BRINGUP] JointStateBroadcaster ACTIVE."
            ),
            LogInfo(
                msg="[REAL BRINGUP] Starting fairino3_controller..."
            ),
            arm_controller_spawner,
        ]


    def after_arm_controller(event, context):

        if event.returncode != 0:
            return [
                LogInfo(
                    msg="[REAL BRINGUP] fairino3_controller FAILED."
                ),
                EmitEvent(
                    event=Shutdown(
                        reason="fairino3_controller failed"
                    )
                ),
            ]

        return [
            LogInfo(
                msg="[REAL BRINGUP] fairino3_controller ACTIVE."
            ),
            LogInfo(
                msg="[REAL BRINGUP] Starting MoveIt, RViz, and workcell scene."
            ),
            move_group,
            rviz,
            workcell_scene_loader,
        ]


    # ============================================================
    # Launch description
    #
    # Register handlers BEFORE starting controller_manager so
    # OnProcessStart / OnProcessExit are not missed.
    # hardware_spawner is NOT started here.
    # ============================================================

    return LaunchDescription([

        LogInfo(
            msg=(
                "[REAL BRINGUP] T_world_base from stage4_config.yaml "
                f"xyz=({install_x:.3f}, {install_y:.3f}, {install_z:.3f}) "
                f"xyzw=({install_qx:.6f}, {install_qy:.6f}, "
                f"{install_qz:.6f}, {install_qw:.6f})"
            )
        ),

        RegisterEventHandler(
            OnProcessStart(
                target_action=controller_manager,
                on_start=[
                    LogInfo(
                        msg="[REAL BRINGUP] Waiting for FR3RealSystem registration..."
                    ),
                    wait_hardware_present,
                ],
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_hardware_present,
                on_exit=after_hardware_present,
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=hardware_spawner,
                on_exit=after_hardware_spawner,
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_hardware_active,
                on_exit=after_hardware_active,
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=joint_state_spawner,
                on_exit=after_joint_state,
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=arm_controller_spawner,
                on_exit=after_arm_controller,
            )
        ),

        world_to_base_tf,

        robot_state_publisher,

        controller_manager,
    ])