/***********************************************
公司：轮趣科技(东莞)有限公司
品牌：WHEELTEC
官网：wheeltec.net
淘宝店铺：shop114407458.taobao.com 
速卖通: https://minibalance.aliexpress.com/store/4455017
版本：V1.0
修改时间：2022-10-13

Brand: WHEELTEC
Website: wheeltec.net
Taobao shop: shop114407458.taobao.com 
Aliexpress: https://minibalance.aliexpress.com/store/4455017
Version: V1.0
Update：2022-10-13

All rights reserved
***********************************************/
#ifndef __CONTROL_H
#define __CONTROL_H
#include "sys.h"

#define PI 3.14159265
#define FILTERING_TIMES  10
extern	int Balance_Pwm,Velocity_Pwm,Turn_Pwm;
int EXTI15_10_IRQHandler(void);
u8 Kinematic_Analysis(float x,float y,float Beta,float Alpha,float Gamma);
void Set_Pwm(float velocity1,float velocity2);
void Xianfu_Pwm(void);
void Xianfu_Velocity(void);
u8 Turn_Off( int voltage);
void Get_Angle(u8 way);
int myabs(int a);
void Control(float Step);
float Position_PID_1(float Position,float Target);
float Position_PID_2(float Position,float Target);
void Usart_Control(void);
void Key_Scan(void);

typedef struct {
    double kp; // 比例增益
    double ki; // 积分增益
    double kd; // 微分增益
    double setpoint; // 设定点
    double integral; // 积分项
    double last_error; // 上一次的误差
    double last_input; // 上一次的输入
} PIDController;

void PID_Init(PIDController *pid, double kp, double ki, double kd);
extern PIDController FollowPID_X,FollowPID_Y;

extern uint8_t send_k210_flag;
extern uint8_t seltec_vaule;
extern uint8_t send_k210_flag;
#endif
