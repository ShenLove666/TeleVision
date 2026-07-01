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
#include "stdio.h"	
#include "sys.h" 


void uart_init(u32 bound);
void usart1_send(u8 data);
void USART1_IRQHandler(void);
void usart1_sendAngleBlock(int Angle_A, int Angle_B);
void USART1_Init(void);

extern u8 get_uart1_count;

#endif


