#include <math.h>

#include "control.h"

#include "adc.h"
#include "key.h"
#include "usart.h"
#include "LED.h"

#include "stm32f10x.h"

/********************************************
*                                           *
*               内部变量                     *
*                                           *
********************************************/
//电池电压采集辅组变量
static int Voltage_All = 0;
static uint8_t Voltage_Count = 0;
static uint16_t reach_FilterCount = 0;

static float target_limit_float(float insert,float low,float high);
static uint8_t target_limit_u8(uint8_t insert,uint8_t low,uint8_t high);
static float PI_Compute(float target, float curr);

/********************************************
*                                           *
*               全局变量                     *
*                                           *
********************************************/
float Voltage;//电池电压
float PTZ_NowAngle = 0;//云台当前的角度
float PTZ_TargetAngle = 0; //云台目标角度
uint8_t PTZ_ControlStep = 30;//云台控制步进值
uint8_t select_mode = 0;
uint8_t target_reach_flag = 0;

//舵机速度控制。控制数值范围在 -400~400，对应舵机的正反转以及最大速度
int servo_speed_control(int speed) {
    // 限制输入范围
    if (speed > 400) speed = 400;
    if (speed < -400) speed = -400;
    
	int pwm = 0;
	
	if( speed > 0 )
		pwm = 1600 + speed;  //1500~1600是大致正方向死区的位置
	else if( speed < 0 )
		pwm = 1400 + speed;  //1400~1500是大致反方向死区的位置
    else pwm = 1500;
	
    return pwm;
}

int target_pwm = 0;

//定时器2更新中断
void TIM2_IRQHandler(void)
{
	
	if (TIM_GetITStatus(TIM2, TIM_IT_Update) != RESET)
	{   
		TIM_ClearITPendingBit(TIM2, TIM_IT_Update); 
	
		
		uint8_t keystate = KEY_Scan(100,0);
		switch(keystate)
		{
			case single_click:
				target_pwm+=50;
				break;
			case double_click:
				target_pwm-=50;
				break;
			case long_click:
				target_pwm=0;
				break;
		}
		
		if( target_pwm > 400 ) target_pwm = 400;
		if( target_pwm <-400 ) target_pwm = -400;
		
		// 输出到舵机
		TIM4->CCR3 = servo_speed_control(target_pwm);
		TIM4->CCR4 = servo_speed_control(target_pwm);

		
		//采集电池电压
		Voltage_All+=Get_battery_volt();
		if(++Voltage_Count==100) Voltage=(float)Voltage_All/10000.0f,Voltage_All=0,Voltage_Count=0,LED=!LED;
	}
}

