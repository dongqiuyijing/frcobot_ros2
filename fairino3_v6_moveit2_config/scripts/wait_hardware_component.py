#!/usr/bin/env python3
"""Wait until a ros2_control hardware component is present or active.

Queries /controller_manager/list_hardware_components. Does not parse CLI output.
Exit 0 on success, non-zero on timeout or service failure.
"""

from __future__ import annotations

import argparse
import sys
import time

import rclpy
from controller_manager_msgs.srv import ListHardwareComponents
from rclpy.node import Node
from rclpy.utilities import remove_ros_args


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for a ros2_control hardware component state"
    )
    parser.add_argument("--component", required=True, help="Hardware component name")
    parser.add_argument(
        "--state",
        required=True,
        choices=("present", "active"),
        help="present: name is listed; active: name listed and state.label=active",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--controller-manager",
        default="/controller_manager",
        help="controller_manager node name",
    )
    non_ros_args = remove_ros_args(args=sys.argv)[1:]
    return parser.parse_args(non_ros_args)


def find_component(response, name: str):
    for component in response.component:
        if component.name == name:
            return component
    return None


def main() -> int:
    args = parse_args()
    rclpy.init(args=sys.argv)
    node = Node("wait_hardware_component")
    cm = args.controller_manager.rstrip("/")
    if not cm.startswith("/"):
        cm = "/" + cm
    service_name = f"{cm}/list_hardware_components"
    client = node.create_client(ListHardwareComponents, service_name)

    deadline = time.monotonic() + max(args.timeout, 0.1)
    node.get_logger().info(
        f"waiting for {args.component} state={args.state} via {service_name} "
        f"(timeout={args.timeout:.1f}s)"
    )

    while time.monotonic() < deadline and rclpy.ok():
        if client.wait_for_service(timeout_sec=0.25):
            break
    if not client.service_is_ready():
        node.get_logger().error(
            f"timeout: service {service_name} not available"
        )
        rclpy.shutdown()
        return 1

    request = ListHardwareComponents.Request()
    last_label = None
    while time.monotonic() < deadline and rclpy.ok():
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=1.0)
        if not future.done():
            continue
        result = future.result()
        if result is None:
            continue
        component = find_component(result, args.component)
        if component is None:
            last_label = "missing"
        else:
            last_label = component.state.label
            if args.state == "present":
                node.get_logger().info(
                    f"{args.component} registered, state.label={last_label}"
                )
                rclpy.shutdown()
                return 0
            if last_label == "active":
                node.get_logger().info(
                    f"{args.component} ACTIVE verified, state.label={last_label}"
                )
                rclpy.shutdown()
                return 0
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            break
        time.sleep(min(0.25, remaining))

    node.get_logger().error(
        f"timeout waiting for {args.component} state={args.state} "
        f"(last seen: {last_label})"
    )
    rclpy.shutdown()
    return 1


if __name__ == "__main__":
    sys.exit(main())
