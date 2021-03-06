cmake_minimum_required(VERSION 2.8.3)
project(goldorak_base)

add_definitions("-std=c++11")
set(SRC src)
set(TEST tests)
set(UAVCAN_SRC_DIR ../uavcan)
set(UAVCAN_LIB $ENV{UAVCAN_LIB})

include_directories(
    ${SRC}
    ${UAVCAN_SRC_DIR}/libuavcan/include/
    ${UAVCAN_SRC_DIR}/libuavcan_drivers/linux/include/
    ${UAVCAN_SRC_DIR}/libuavcan_drivers/posix/include/
    ${UAVCAN_SRC_DIR}/libuavcan/dsdl_compiler/dsdlc_generated/
    ${catkin_INCLUDE_DIRS}
)

find_package(catkin REQUIRED COMPONENTS
    cvra_msgs
    dynamic_reconfigure
    roscpp
    rospy
    std_msgs
    sensor_msgs
    nav_msgs
    geometry_msgs
    tf
    nodelet
    message_generation
)

# Generate service messages in 'srv' folder
add_service_files(
    FILES
    FishingAxisControl.srv
)
generate_messages(
    DEPENDENCIES
    std_msgs
)

generate_dynamic_reconfigure_options(
    cfg/PID.cfg
    cfg/MotorBoard.cfg
    cfg/EnableMotor.cfg
    cfg/FeedbackStream.cfg
)

catkin_package(
    DEPENDS roscpp nodelet
)

find_library(UAVCAN_LIB uavcan REQUIRED)

add_executable(
    uc_publisher
    ${SRC}/uc_publisher.cpp
    ${SRC}/platform_linux.cpp
    )
target_link_libraries(uc_publisher ${UAVCAN_LIB} rt ${catkin_LIBRARIES})

add_executable(
    motor_config_server
    ${SRC}/motor_config_server.cpp
    ${SRC}/platform_linux.cpp
)
target_link_libraries(motor_config_server ${UAVCAN_LIB} rt ${catkin_LIBRARIES})
add_dependencies(motor_config_server ${PROJECT_NAME}_gencfg)

add_executable(
    motor_config_send_once
    ${SRC}/motor_config_send_once.cpp
    ${SRC}/platform_linux.cpp
)
target_link_libraries(motor_config_send_once ${UAVCAN_LIB} rt ${catkin_LIBRARIES})

add_executable(
    uc_config_server
    ${SRC}/uc_config_server.cpp
    ${SRC}/platform_linux.cpp
    )
target_link_libraries(uc_config_server ${UAVCAN_LIB} rt ${catkin_LIBRARIES})

add_executable(
    uavcan_bridge
    ${SRC}/uavcan_bridge.cpp
    ${SRC}/platform_linux.cpp
)
target_link_libraries(uavcan_bridge ${UAVCAN_LIB} rt ${catkin_LIBRARIES} ${Boost_LIBRARIES})
add_dependencies(uavcan_bridge cvra_msgs)


## Create the joint state publisher nodelet library
add_library(
    joint_state_publisher_nodelet
    ${SRC}/joint_state_publisher_nodelet.cpp
)
target_link_libraries(joint_state_publisher_nodelet rt ${catkin_LIBRARIES})
if(catkin_EXPORTED_LIBRARIES)
    add_dependencies(joint_state_publisher_nodelet ${catkin_EXPORTED_LIBRARIES})
endif()

## Create the odometry nodelet library
add_library(
    odometry_nodelet
    ${SRC}/odometry_nodelet.cpp
    ${SRC}/odometry/odometry.c
)
target_link_libraries(odometry_nodelet rt ${catkin_LIBRARIES} ${Boost_LIBRARIES})
if(catkin_EXPORTED_LIBRARIES)
    add_dependencies(odometry_nodelet ${catkin_EXPORTED_LIBRARIES})
endif()

## Create the controller nodelet library
add_library(
    controller_nodelet
    ${SRC}/controller_nodelet.cpp
)
target_link_libraries(controller_nodelet rt ${catkin_LIBRARIES} ${Boost_LIBRARIES})
if(catkin_EXPORTED_LIBRARIES)
    add_dependencies(controller_nodelet ${catkin_EXPORTED_LIBRARIES})
endif()

## Create the fishing module controller nodelet library
add_library(
    fishing_nodelet
    ${SRC}/fishing_nodelet.cpp
)
target_link_libraries(fishing_nodelet rt ${catkin_LIBRARIES} ${Boost_LIBRARIES})
if(catkin_EXPORTED_LIBRARIES)
    add_dependencies(fishing_nodelet goldorak_base_generate_messages_cpp ${catkin_EXPORTED_LIBRARIES})
else()
    add_dependencies(fishing_nodelet goldorak_base_generate_messages_cpp)
endif()

## Mark the nodelet library for installations
install(TARGETS
    joint_state_publisher_nodelet
    odometry_nodelet
    controller_nodelet
    fishing_nodelet
    ARCHIVE DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
    RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

## Mark other files for installation (e.g. launch and bag files, etc.)
install(FILES
    nodelets.xml
    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
install(DIRECTORY
    launch
    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)


# Build tests
if(CATKIN_ENABLE_TESTING)
    find_package(rostest REQUIRED)

    add_rostest_gtest(motor_param_test
                     ${TEST}/motor_param_test.launch
                     ${TEST}/motor_param_test.cpp)
    target_link_libraries(motor_param_test ${UAVCAN_LIB} rt pthread ${catkin_LIBRARIES})

    add_rostest_gtest(proximity_beacon_driver_test
                     ${TEST}/proximity_beacon_driver_test.launch
                     ${TEST}/proximity_beacon_driver_test.cpp)
    target_link_libraries(proximity_beacon_driver_test ${UAVCAN_LIB} rt pthread ${catkin_LIBRARIES})
endif()
