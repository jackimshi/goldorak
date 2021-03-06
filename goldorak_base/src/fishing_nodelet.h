#ifndef FISHING_NODELET_H
#define FISHING_NODELET_H

#include <nodelet/nodelet.h>

#include <std_msgs/Float32.h>
#include <goldorak_base/FishingAxisControl.h>

namespace goldorak_base
{
    class fishing_nodelet : public nodelet::Nodelet
    {
        public:
            fishing_nodelet();
            virtual void onInit();

        private:
            float y_range, y_index, z_range, z_index, impeller_speed_range, y_offset, z_offset, z_torque_down;
            int y_direction, z_direction, impeller_direction;
            bool y_on, z_on, impeller_on;

            ros::Subscriber y_index_sub, z_index_sub;
            ros::Publisher y_position_pub, z_position_pub, impeller_speed_pub;
            ros::ServiceServer y_axis_server, z_axis_server, impeller_server;

            ros::Timer timer;

            void y_index_cb(const std_msgs::Float32ConstPtr& msg);
            bool y_control_cb(
                goldorak_base::FishingAxisControl::Request  &req,
                goldorak_base::FishingAxisControl::Response &res);

            void z_index_cb(const std_msgs::Float32ConstPtr& msg);
            bool z_control_cb(
                goldorak_base::FishingAxisControl::Request  &req,
                goldorak_base::FishingAxisControl::Response &res);

            bool impeller_control_cb(
                goldorak_base::FishingAxisControl::Request  &req,
                goldorak_base::FishingAxisControl::Response &res);

            void timer_cb(const ros::TimerEvent&);
    };
}

#endif /* FISHING_NODELET_H */
