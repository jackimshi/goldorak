#!/usr/bin/env python

import argparse
from math import radians

import rospy
import roslib
import actionlib
from cvra_msgs.msg import MotorControlSetpoint
from move_base_msgs.msg import MoveBaseGoal, MoveBaseAction
from actionlib_msgs.msg import GoalID

from smach import StateMachine, State, Sequence

from smach_ros import SimpleActionState, IntrospectionServer

from geometry_msgs.msg import Quaternion
from tf.transformations import quaternion_from_euler
from goldorak_base.srv import FishingAxisControl

import reset_pose
import starter
import move_base_override

FISHING_Y_AXIS_SERVICE = 'fishing_y_axis_control'
FISHING_Z_AXIS_SERVICE = 'fishing_z_axis_control'
FISHING_IMPELLER_SERVICE = 'fishing_impeller_control'

GAME_DURATION = 90

class Transitions:
    SUCCESS = 'succeeded'
    FAILURE = 'failure'

class Team:
    GREEN = 'green'
    VIOLET = 'violet'

TEAM = Team.GREEN

def mirror_point(x, y):
    if TEAM == Team.VIOLET:
        return x, y
    elif TEAM == Team.GREEN:
        return 3.0 - x, y

    raise ValueError("Unknown team")


def fishing_y_axis_deploy(state):
    rospy.wait_for_service(FISHING_Y_AXIS_SERVICE)

    f = rospy.ServiceProxy(FISHING_Y_AXIS_SERVICE, FishingAxisControl)
    f(state)

def fishing_z_axis_deploy(state):
    rospy.wait_for_service(FISHING_Z_AXIS_SERVICE)

    f = rospy.ServiceProxy(FISHING_Z_AXIS_SERVICE, FishingAxisControl)
    f(state)

def init_robot_pose():
    # Initialise robot pose
    x, y = mirror_point(0.105, 0.900 + 0.21 / 2)

    if TEAM == Team.VIOLET:
        reset_pose.reset(x, y, radians(0))
    else:
        reset_pose.reset(x, y, radians(-180))


class WaitStartState(State):
    def __init__(self):
        State.__init__(self, outcomes=[Transitions.SUCCESS])
        self.abort_navigation_pub = rospy.Publisher('move_base/cancel', GoalID, queue_size=1)
        self.umbrella_pub = rospy.Publisher('/umbrella/setpoint', MotorControlSetpoint, queue_size=1)

    def end_of_game_cb(self, event):
        rospy.loginfo("End of game")
        rospy.loginfo("Cancelling move_base actions")
        self.abort_navigation_pub.publish(GoalID())

        # Opens umbrella
        rospy.loginfo("Opening umbrella")
        rate = rospy.Rate(10) # 10hz

        for i in range(50):
            msg = MotorControlSetpoint(node_name="umbrella", voltage=12,
                    mode = MotorControlSetpoint.MODE_CONTROL_VOLTAGE)
            self.umbrella_pub.publish(msg)
            rate.sleep()

        msg = MotorControlSetpoint(node_name="umbrella", voltage=0,
                mode = MotorControlSetpoint.MODE_CONTROL_VOLTAGE)
        self.umbrella_pub.publish(msg)

        rospy.loginfo("Umbrella openend")

    def wait_for_starter(self):
        while not starter.poll(): # activate at falling edge
            rospy.sleep(0.1)


    def execute(self, userdata):
        rospy.loginfo('Waiting for start')
        self.wait_for_starter()

        # Reinitialise robot pose
        init_robot_pose()

        rospy.loginfo('Starting...')

        rospy.Timer(rospy.Duration(GAME_DURATION), self.end_of_game_cb, oneshot=True)

        return Transitions.SUCCESS

def add_waypoints(waypoints):
    for key, (x, y), angle in waypoints:
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = 'odom'
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation = Quaternion(*quaternion_from_euler(0, 0, radians(angle)))

        Sequence.add(key, SimpleActionState('move_base', MoveBaseAction, goal=goal),
                transitions={'preempted': Transitions.FAILURE, 'aborted': Transitions.FAILURE})


def create_door_state_machine(door_x):
    seq = Sequence(outcomes=[Transitions.SUCCESS, Transitions.FAILURE],
                   connector_outcome=Transitions.SUCCESS)

    waypoints = (
        ('approach', mirror_point(door_x, 1.5), 90),
        ('close', mirror_point(door_x, 1.8), 90),
        ('back_out', mirror_point(door_x, 1.5), 90),
    )

    with seq:
        add_waypoints(waypoints)

    return seq

class FishAndHoldState(State):
    def __init__(self):
        State.__init__(self, outcomes=[Transitions.SUCCESS])

    def execute(self, userdata):
        rospy.loginfo("Opening fishing module")
        fishing_y_axis_deploy(True)
        rospy.sleep(2)
        # fishing_z_axis_deploy(True)
        # rospy.sleep(1)

        rospy.loginfo("Fishing...")

        # fishing_z_axis_deploy(False)
        # rospy.sleep(2)

        rospy.loginfo("Holding fishing module")

        return Transitions.SUCCESS

class FishDropState(State):
    def __init__(self):
        State.__init__(self, outcomes=[Transitions.SUCCESS])

    def execute(self, userdata):
        rospy.loginfo("Dropping fish")

        return Transitions.SUCCESS


class FishCloseState(State):
    def __init__(self):
        State.__init__(self, outcomes=[Transitions.SUCCESS])

    def execute(self, userdata):
        rospy.wait_for_service(FISHING_Y_AXIS_SERVICE)

        rospy.loginfo("Closing fishing module")
        fishing_y_axis_deploy(False)
        rospy.sleep(1)

        return Transitions.SUCCESS

class FishApproachState(State):
    def __init__(self):
        State.__init__(self, outcomes=[Transitions.SUCCESS])

    def execute(self, userdata):
        for i in range(10):
            move_base_override.move(0.05)
            rospy.sleep(0.1)

        for i in range(10):
            move_base_override.move(-0.02)
            rospy.sleep(0.1)

        return Transitions.SUCCESS


def create_fish_sequence():
    seq = Sequence(outcomes=[Transitions.SUCCESS, Transitions.FAILURE],
                   connector_outcome=Transitions.SUCCESS)

    margin = 0.11
    approach = (
        ('approach', mirror_point(0.73, 0.3), -90),
        ('approach2', mirror_point(0.73, 0.15), -90),
        # ('orientation', mirror_point(0.73, margin), -180),
    )

    drop = (
        ('drop', mirror_point(1.5, margin), -180),
        ('drop2', mirror_point(1.5, margin), -180),
    )

    with seq:
        add_waypoints(approach)
        Sequence.add('calage', FishApproachState())
        Sequence.add('grab_fish', FishAndHoldState())
        #add_waypoints(drop)
        #Sequence.add('drop_fish', FishDropState())
        Sequence.add('end_fishing', FishCloseState())

    return seq


def main():
    rospy.init_node('smach_example_state_machine')

    init_robot_pose()
    move_base_override.init()

    sq = Sequence(outcomes=[Transitions.SUCCESS, Transitions.FAILURE],
                  connector_outcome=Transitions.SUCCESS)
    with sq:
        Sequence.add('waiting', WaitStartState())
        add_waypoints(('get_out', mirror_point(0.6, 1.0), -180))
        Sequence.add('fishing', create_fish_sequence())
        # Sequence.add('inner_door', create_door_state_machine(0.3))
        # Sequence.add('outer_door', create_door_state_machine(0.6))

    # Create and start the introspection server
    sis = IntrospectionServer('strat', sq, '/strat')
    sis.start()

    # Execute the state machine
    outcome = sq.execute()

    # Wait for ctrl-c to stop the application
    rospy.spin()
    sis.stop()

if __name__ == '__main__':
    main()
