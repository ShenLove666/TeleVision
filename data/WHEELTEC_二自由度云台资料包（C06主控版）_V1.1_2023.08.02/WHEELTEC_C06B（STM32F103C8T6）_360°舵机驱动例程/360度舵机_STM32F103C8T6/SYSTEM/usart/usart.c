#include <stdio.h>
#include <string.h>

#include "usart.h"
#include "stm32f10x.h"

#include "control.h"

//////////////////////////////////////////////////////////////////
//加入以下代码,支持printf函数,而不需要选择use MicroLIB	  
#if 1
#pragma import(__use_no_semihosting)             
//标准库需要的支持函数                 
struct __FILE 
{ 
	int handle; 
}; 

FILE __stdout;       
//定义_sys_exit()以避免使用半主机模式    
void _sys_exit(int x) 
{ 
	x = x; 
} 
//重定义fputc函数 
int fputc(int ch, FILE *f)
{ 	
	while((USART1->SR&0X40)==0);//循环发送,直到发送完毕   
	USART1->DR = (u8) ch;      
	return ch;
}
#endif

uint8_t Calculate_BBC(const uint8_t* checkdata,uint16_t datalen)
{
	char bccval = 0;
	for(uint16_t i=0;i<datalen;i++)
	{
		bccval ^= checkdata[i];
	}
	return bccval;
}

//软复位进BootLoader区域
static void _System_Reset_(u8 uart_recv)
{
	static u8 res_buf[5];
	static u8 res_count=0;
	
	res_buf[res_count]=uart_recv;
	
	if( uart_recv=='r'||res_count>0 )
		res_count++;
	else
		res_count = 0;
	
	if(res_count==5)
	{
		res_count = 0;
		//接受到上位机请求的复位字符“reset”，执行软件复位
		if( res_buf[0]=='r'&&res_buf[1]=='e'&&res_buf[2]=='s'&&res_buf[3]=='e'&&res_buf[4]=='t' )
		{
			NVIC_SystemReset();//进行软件复位，复位后执行 BootLoader 程序
		}
	}
}


//串口发送与接收数据定义
ReportDataSend_t ReportSendpack = { 0 };//数据发送包
ReportDataRecv_t ReportRecvpack = { 0 };//数据接受包

//发送数据长度与数据包
static const uint16_t report_send_bufferLen = sizeof(ReportDataSend_t);
static uint8_t report_send_buffer[report_send_bufferLen] = { 0 };

//接收数据长度与数据包
static const uint16_t report_recv_bufferLen = sizeof(ReportDataRecv_t);
static uint8_t report_recv_buffer[report_recv_bufferLen] = { 0 };

//发送数据到ROS端
void report_to_ros(void)
{
	ReportSendpack.head1 = 0x1F;
	ReportSendpack.head2 = 0xF1;
	ReportSendpack.arrive_flag = target_reach_flag;//目标位置到达标志位
	ReportSendpack.control_step = PTZ_ControlStep;//当前步进值
	ReportSendpack.NowAngle = PTZ_NowAngle;//当前角度
	
	//将需要发送的数据赋值
	memcpy(report_send_buffer,&ReportSendpack,sizeof(ReportDataSend_t));
	
	//执行BCC校验
	report_send_buffer[report_send_bufferLen-1] = Calculate_BBC(report_send_buffer,report_send_bufferLen-1);
	
	//启动发送
	DMA_Cmd(DMA1_Channel4, DISABLE);
	DMA_SetCurrDataCounter(DMA1_Channel4,report_send_bufferLen);
    DMA_Cmd(DMA1_Channel4, ENABLE);
}



void usart1_init(uint32_t baud)
{
	GPIO_InitTypeDef GPIO_InitStructure;
	USART_InitTypeDef USART_InitStructure;
	NVIC_InitTypeDef NVIC_InitStrue;

	RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1,ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA,ENABLE);
	RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);
	
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
	GPIO_Init(GPIOA, &GPIO_InitStructure);

	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
	GPIO_Init(GPIOA, &GPIO_InitStructure);

	USART_InitStructure.USART_BaudRate = baud;
	USART_InitStructure.USART_WordLength = USART_WordLength_8b;
	USART_InitStructure.USART_StopBits = USART_StopBits_1;
	USART_InitStructure.USART_Parity = USART_Parity_No;
	USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
	USART_InitStructure.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
	USART_Init(USART1, &USART_InitStructure);
	USART_Cmd(USART1, ENABLE); 

    //配置 DMA1 通道 4（USART1_TX）
    DMA_InitTypeDef DMA_InitStructure;
    DMA_InitStructure.DMA_PeripheralBaseAddr = (uint32_t)&USART1->DR;
    DMA_InitStructure.DMA_MemoryBaseAddr = (uint32_t)report_send_buffer;
    DMA_InitStructure.DMA_DIR = DMA_DIR_PeripheralDST;
    DMA_InitStructure.DMA_BufferSize = report_send_bufferLen;
    DMA_InitStructure.DMA_PeripheralInc = DMA_PeripheralInc_Disable;//外设寄存器不自增
    DMA_InitStructure.DMA_MemoryInc = DMA_MemoryInc_Enable;         //内存自增
    DMA_InitStructure.DMA_PeripheralDataSize = DMA_PeripheralDataSize_Byte;//外设数据宽度
    DMA_InitStructure.DMA_MemoryDataSize = DMA_MemoryDataSize_Byte;        //内存数据宽度
    DMA_InitStructure.DMA_Mode = DMA_Mode_Normal;      //普通模式
    DMA_InitStructure.DMA_Priority = DMA_Priority_High;//优先级
    DMA_InitStructure.DMA_M2M = DMA_M2M_Disable;       //内存到内存搬运
    DMA_Init(DMA1_Channel4, &DMA_InitStructure);
	DMA_Cmd (DMA1_Channel4,ENABLE);
	USART_DMACmd(USART1, USART_DMAReq_Tx, ENABLE);
	
	USART_ITConfig(USART1,USART_IT_RXNE,ENABLE);
	NVIC_InitStrue.NVIC_IRQChannel=USART1_IRQn;
	NVIC_InitStrue.NVIC_IRQChannelCmd=ENABLE;
	NVIC_InitStrue.NVIC_IRQChannelPreemptionPriority=5;//抢占优先级
	NVIC_InitStrue.NVIC_IRQChannelSubPriority=0;
	NVIC_Init(&NVIC_InitStrue);
}

/**************************************************************************
函数功能：串口1中断服务函数
入口参数：无
返回  值：无
**************************************************************************/
extern void update_PTZTarget(ReportDataRecv_t* p);

void USART1_IRQHandler(void)
{
	static uint8_t last_recv;
	static uint8_t report_recv_count = 0;
	static uint8_t report_recv_statemachine = 0;
	
	uint8_t recv = 0;
	
    if(USART_GetITStatus(USART1, USART_IT_RXNE)) //接收到数据
    {
		recv = USART_ReceiveData(USART1);
		_System_Reset_(recv);
		
		//简单状态机
		enum{
			Wait_HEAD=0       ,//等待正式数据阶段
			Wait_FrameOver   ,//等待一帧数据接收完毕
		};
		
		//数据接收流程
		switch( report_recv_statemachine )
		{
			case Wait_HEAD://等待帧头
			{
				if(recv==0xFA && last_recv==0xAF)
				{
					report_recv_buffer[0] = 0xAF;
					report_recv_buffer[1] = 0xFA;
					report_recv_count = 2;
					report_recv_statemachine = Wait_FrameOver;
				}
				break;
			}
			case Wait_FrameOver: //等待一帧数据结束
			{
				report_recv_buffer[report_recv_count++] = recv;
				if( report_recv_count == report_recv_bufferLen )
				{	
					//检查校验位是否正确
					if(report_recv_buffer[report_recv_bufferLen-1] == Calculate_BBC(report_recv_buffer,report_recv_bufferLen-1))
					{
						//数据赋值解析
						memcpy(&ReportRecvpack,report_recv_buffer,sizeof(ReportDataRecv_t));
						
						//云台数据更新
//						update_PTZTarget(&ReportRecvpack);
					}
					
					//等待下一次数据接收
					report_recv_count = 0;
					report_recv_statemachine = Wait_HEAD;
				}
				break;
			}
		}
		last_recv = recv;
    }
}





