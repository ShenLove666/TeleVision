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
#include "show.h"

unsigned char i;          //计数变量
unsigned char Send_Count; //串口需要发送的数据个数
float Vol;
/**************************************************************************
函数功能：OLED显示
入口参数：无
返回  值：无
**************************************************************************/
extern uint8_t seltec_vaule;
void oled_show(void)
{  
	int row_Mode=0;
  int row_PS2KEY=10;		
	int row_Voltage=20;
	int row_Target=30;	
	int row_motor1=40;	
	int row_motor2=50;	
	
	OLED_ShowString(0,row_PS2KEY,"Num: ");
	OLED_ShowNumber(65,row_PS2KEY,show_num,2,12);
	
	     if( seltec_vaule==0 )  OLED_ShowString(0,0,"Blue  ");
	else if( seltec_vaule==1 )  OLED_ShowString(0,0,"Green ");
	else if( seltec_vaule==2 )  OLED_ShowString(0,0,"Yellow");
	else if( seltec_vaule==3 )  OLED_ShowString(0,0,"Red   ");
		
//	OLED_ShowString(0,row_Mode,"Mode:");
//	if(Mode_Usart_PS2)OLED_ShowString(65,row_Mode,"Usart");
//	else OLED_ShowString(65,row_Mode,"PS2  ");

	OLED_ShowString(0,row_Voltage,"Voltage:");
	OLED_ShowString(78,row_Voltage,".");
	OLED_ShowString(100,row_Voltage,"V");
	OLED_ShowNumber(65,row_Voltage,Voltage/100,2,12);
	OLED_ShowNumber(88,row_Voltage,Voltage%100,2,12);
	
	if(Voltage%100<10) 	OLED_ShowNumber(82,row_Voltage,0,2,12);
	
	OLED_ShowString(00,row_Target,"Target");
	OLED_ShowString(60,row_Target,"Position");
	//=============显示云台舵机的状态=======================//	
	
	OLED_ShowString(0,row_motor1,"+"),
	OLED_ShowNumber(15,row_motor1, ObjectTrack.cam_centerX,6,12); 

	OLED_ShowString(60,row_motor1,"+"),
	OLED_ShowNumber(75,row_motor1, ObjectTrack.centerX,6,12);
	
	//=============显示外臂舵机的状态=======================//	
	OLED_ShowString(0,row_motor2,"+"),
	OLED_ShowNumber(15,row_motor2, ObjectTrack.cam_centerY,6,12); 
	OLED_ShowString(60,row_motor2,"+"),
	OLED_ShowNumber(75,row_motor2,  ObjectTrack.centerY,6,12);
	
//	OLED_ShowString(0,row_motor1,"+"),
////	OLED_ShowNumber(15,row_motor1, Target1,6,12); 
//	OLED_ShowNumber(15,row_motor1, k210_recv.face_x,6,12); 

//	OLED_ShowString(60,row_motor1,"+"),
//	OLED_ShowNumber(75,row_motor1, get_uart1_count,6,12);
//	
//	//=============显示外臂舵机的状态=======================//	
//	OLED_ShowString(0,row_motor2,"+"),
//	OLED_ShowNumber(15,row_motor2, Target2,6,12); 
//	OLED_ShowString(60,row_motor2,"+"),
//	OLED_ShowNumber(75,row_motor2, Position2,6,12);

	//=============刷新=======================//
	OLED_Refresh_Gram();	
	}
/**************************************************************************
函数功能：向APP发送数据
入口参数：无
返回  值：无
作    者：平衡小车之家
**************************************************************************/
void APP_Show(void)
{    
		static u8 flag;
	  int app_2,app_3,app_4;
		app_4=(Voltage-1110)*2/3;		if(app_4<0)app_4=0;if(app_4>100)app_4=100;   //对电压数据进行处理
//    app_3=Moto1/50; if(app_3<0)app_3=-app_3;			                           //对编码器数据就行数据处理便于图形化
//		app_2=Moto2/50;  if(app_2<0)app_2=-app_2;
	  flag=!flag;
   if(flag==0)// 
   printf("{A%d:%d:%d:%d}$",(u8)app_2,(u8)app_3,(u8)app_4,0);//打印到APP上面
	 else
	 printf("{B%d:%d}$",(int)Position1,(int)Position2);//打印到APP上面 显示波形
}

