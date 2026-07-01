#ifndef __CONTROL_H
#define __CONTROL_H

#include <stdint.h>


#define ANGLE_PWM_K 2.7777777777f

extern float Voltage;
extern float PTZ_NowAngle,PTZ_TargetAngle;
extern uint8_t PTZ_ControlStep,select_mode,target_reach_flag;

#endif
