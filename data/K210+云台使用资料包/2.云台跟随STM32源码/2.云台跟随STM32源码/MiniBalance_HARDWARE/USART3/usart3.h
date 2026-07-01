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
#ifndef __USRAT3_H
#define __USRAT3_H 
#include "sys.h"


//K210传输数据组

#define K210_HEAD 0xCC
#define K210_END  0xDD

#pragma pack(1) 
struct K210_Recvmsg{
	u8 Head;          //帧头
	u16 Cam_W; 
	u16 Cam_H; 
	u16 follow_x; 
	u16 follow_y; 
	u8 BCCcheck;     //BCC校验
	u8 End;          //帧尾
};
#pragma pack() //数据包定义结束,恢复默认


#pragma pack(1) 
struct Send_K210msg{
	u8 Head;          //帧头
	u8 select_color; 
	u8 BCCcheck;     //BCC校验
	u8 End;          //帧尾
};
#pragma pack() //数据包定义结束,恢复默认

void K210_data_callback(u8 recv);
extern struct K210_Recvmsg k210_recv; //定义接收数据的数据组
void update_sendmsg_and_Send(uint8_t keyvalue);


//定义跟踪结构体
typedef struct {
	float cam_centerX;
	float cam_centerY;
	float centerX;
	float centerY;
	u8 lost;
	u8 count_Outline;
}OBJECT_TRACK_t;

extern OBJECT_TRACK_t ObjectTrack;

void USART3_Init(void);
void usart3_send(u8 data);
void USART3_IRQHandler(void);
void usart3_sendAngleBlock(int Angle_A, int Angle_B);
extern uint8_t num_flag ,show_num ;

#endif
