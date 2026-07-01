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



/***********************************************************
重要说明
关于舵机控制的说明
舵机的定时器频率为50HZ
控制舵机运动的占空比数值范围是250-1250，占空比为750时是舵机的正中心位置
控制舵机运动的代码在control.c文件中
***************************************************************/

#include "stm32f10x.h"
#include "sys.h"
#include "control.h"

u8 Flag_Show=0;                //停止标志位和 显示标志位 默认停止 显示打开
float Velocity1,Velocity2;     //电机PWM变量
float Position1=750,Position2=750;
float Speed=10;                   //运动速度设置
int Voltage;                      //电池电压采样相关的变量
u8 delay_50,delay_flag,Bi_zhang=0,PID_Send,Flash_Send; //延时和调参等变量
float Target1=750,Target2=750;     //电机目标值
float	Position_KP=6,Position_KI=0,Position_KD=3;  //位置控制PID参数
int PS2_LX,PS2_LY,PS2_RX,PS2_RY,PS2_KEY;
uint8_t Urxbuf[8]; //串口接收数据数组

int main(void)
{
    delay_init();	    	            //=====延时函数初始化
    
    JTAG_Set(SWD_ENABLE);           //=====打开SWD接口 可以利用主板的SWD接口调试
    BEEP_Init();                    //======蜂鸣器初始化
    BEEP=1;                         //======蜂鸣器开
    LED_Init();                     //=====初始化与 LED 连接的硬件接口
    KEY_Init();                     //=====按键初始化
    MY_NVIC_PriorityGroupConfig(2); //=====中断分组
    delay_ms(100);                  //=====延时等待
    
    Adc_Init();                     //=====adc初始化
    delay_ms(100);                  //=====延时等待
    OLED_Init();                    //=====OLED初始化
    TIM2_Int_Init(99,7199);         //=====定时器10ms中断初始化
    TIM4_PWM_Init(9999,143);        //=====舵机PWM初始化
    PS2_Init();                     //=====PS2手柄初始化
    PS2_SetInit();		 							//=====ps2配置初始化,配置“红绿灯模式”，并选择是否可以修改
    BEEP=0;                         //=====蜂鸣器关
	
	delay_ms(500);
	delay_ms(500);
	USART1_Init();                  //=====USB接口串口初始化
	USART3_Init();                  //=====串口3初始化 B10:TX  B11:RX
	
	PID_Init(&FollowPID_X,0.024,0,0.04);//PID控制器初始化
	PID_Init(&FollowPID_Y,-0.024,-0,-0.04);//PID控制器初始化
    while(1)
    {

		//如果是选择色块跟随的demo可使用,其他demo不使用该功能
		if( send_k210_flag==1 )
		{
			send_k210_flag = 0;
			for(uint8_t i=0;i<2;i++)
				update_sendmsg_and_Send(seltec_vaule);//发送选择何种颜色进行跟踪到k210
		}
		
        oled_show();          //===显示屏打开

    }
}

