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

#include "stm32f10x.h"

#include "sys.h"
#include "delay.h"
#include "usart.h"

#include "led.h"
#include "oled.h"
#include "servo.h"
#include "timer.h"
#include "adc.h"
#include "key.h"

#include "control.h"
	
extern	int target_pwm;
int main(void)
{
	//中断优先级分组
	NVIC_SetPriorityGrouping(NVIC_PriorityGroup_4);
	
	//禁用JATG,使用SWD
	JTAG_Set(JTAG_SWD_DISABLE);
	JTAG_Set(SWD_ENABLE);
	
	//滴答定时器初始化
	SysTick_Init(1000);
	
	//串口1初始化
	usart1_init(230400);
	
	//LED
	LED_Init();
	
	//按键
	KEY_Init();
	
	//OLED
	OLED_Init();
	
	//舵机初始化
	TIM4_PWM_Init(9999,71);//50Hz
	
	//ADC初始化
	Adc_Init();
	
	//定时器初始化（100hz,10ms）
	TIM2_Int_Init(99,7199);
	
	while(1)
	{

		OLED_ShowFloat(0,0,target_pwm,4,2);
		
		OLED_ShowNumber(0,10,TIM4->CCR3,4,12);
		OLED_ShowNumber(0,20,TIM4->CCR4,4,12);
		
		//电压显示
		OLED_ShowFloat(80,50,Voltage,2,2);
		OLED_ShowString(120,50,"V");
		OLED_Refresh_Gram();
	}
	
}


