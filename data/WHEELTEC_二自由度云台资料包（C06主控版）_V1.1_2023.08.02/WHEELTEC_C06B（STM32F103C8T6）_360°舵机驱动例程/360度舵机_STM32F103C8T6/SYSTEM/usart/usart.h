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
#ifndef __USART_H
#define __USART_H

#include <stdint.h>

void usart1_init(uint32_t baud);

#pragma pack(1)
//上报至上位机的数据
typedef struct{
	uint8_t head1; //帧头,规定0x1F 0xF1
	uint8_t head2; 
	uint8_t arrive_flag;  //到达目标角度标志位
	uint8_t control_step; //当前步进值上报
	float NowAngle;      //当前角度上报 
	uint8_t bcccheck;    //bcc校验位
}ReportDataSend_t;

//接收来自上位机的数据
typedef struct{
	uint8_t head1; //帧头,规定0xAF 0xFA
	uint8_t head2; 
	uint8_t control_step;  //步进值修改
	float   TargetAngle;   //目标角度
	uint8_t bcccheck;     //bcc校验位
}ReportDataRecv_t;
#pragma pack()


//串口发送与接收数据定义
extern ReportDataSend_t ReportSendpack ;//数据发送包
extern ReportDataRecv_t ReportRecvpack ;//数据接受包

void report_to_ros(void);

extern uint8_t Calculate_BBC(const uint8_t* checkdata,uint16_t datalen);

#endif


