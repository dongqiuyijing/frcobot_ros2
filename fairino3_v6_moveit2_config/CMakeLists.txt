cmake_minimum_required(VERSION 3.22)
project(fairino3_v6_moveit2_config)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME}
  PATTERN "setup_assistant.launch" EXCLUDE)
install(DIRECTORY config DESTINATION share/${PROJECT_NAME})
install(FILES .setup_assistant DESTINATION share/${PROJECT_NAME})
install(
  PROGRAMS scripts/wait_hardware_component.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME wait_hardware_component
)

ament_package()
