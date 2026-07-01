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
#include "usart3.h"

/**************************************************************************
函数功能：串口3初始化
入口参数：无
返 回 值：无
**************************************************************************/
void USART3_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStrue; //定义一个引脚初始化的结构体
    USART_InitTypeDef USART_InitStrue; //定义一个串口初始化的结构体
    NVIC_InitTypeDef NVIC_InitStrue; //定义一个中断优先级初始化的结构体

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB,ENABLE); //GPIOB时钟使能
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART3,ENABLE); //串口3时钟使能

    GPIO_InitStrue.GPIO_Mode=GPIO_Mode_AF_PP; //B10引脚作为串口3发送数据引脚，推挽复用输出
    GPIO_InitStrue.GPIO_Pin=GPIO_Pin_10; //引脚10
    GPIO_InitStrue.GPIO_Speed=GPIO_Speed_10MHz; //作为串口发送数据引脚时该速度可以为任意
    GPIO_Init(GPIOB,&GPIO_InitStrue); //根据上面设置好的GPIO_InitStructure参数进行初始化
    GPIO_ResetBits(GPIOB, GPIO_Pin_2);

    GPIO_InitStrue.GPIO_Mode=GPIO_Mode_IN_FLOATING; //A10引脚作为串口1接收数据引脚，浮空输入或带上拉输入
    GPIO_InitStrue.GPIO_Pin=GPIO_Pin_11; //引脚11
    GPIO_InitStrue.GPIO_Speed=GPIO_Speed_10MHz; //作为串口接收数据引脚时该速度可以为任意
    GPIO_Init(GPIOB,&GPIO_InitStrue); //根据上面设置好的GPIO_InitStructure参数进行初始化

    USART_InitStrue.USART_BaudRate=9600; //定义串口波特率为9600bit/s
    USART_InitStrue.USART_HardwareFlowControl=USART_HardwareFlowControl_None; //无硬件数据流控制
    USART_InitStrue.USART_Mode=USART_Mode_Tx|USART_Mode_Rx; //发送接收兼容模式
    USART_InitStrue.USART_Parity=USART_Parity_No; //无奇偶校验位
    USART_InitStrue.USART_StopBits=USART_StopBits_1; //一个停止位
    USART_InitStrue.USART_WordLength=USART_WordLength_8b; //字长为8位数据格式
    USART_Init(USART3,&USART_InitStrue);//根据上面设置USART_InitStrue参数初始化串口1

    USART_Cmd(USART3,ENABLE); //使能串口1

    USART_ITConfig(USART3,USART_IT_RXNE,ENABLE); //使能接收中断void USART1_IRQHandler(void)

    NVIC_InitStrue.NVIC_IRQChannel=USART3_IRQn; //属于串口3中断
    NVIC_InitStrue.NVIC_IRQChannelCmd=ENABLE; //中断使能
    NVIC_InitStrue.NVIC_IRQChannelPreemptionPriority=1; //抢占优先级为1级，值越小优先级越高，0级优先级最高
    NVIC_InitStrue.NVIC_IRQChannelSubPriority=1; //响应优先级为1级，值越小优先级越高，0级优先级最高
    NVIC_Init(&NVIC_InitStrue); ////根据NVIC_InitStrue的参数初始化VIC寄存器，设置串口1中断优先级
}


/////////// 定义向k210传输数据的数组 ///////////////////
struct Send_K210msg send_k210msg;
uint8_t send_len = sizeof( send_k210msg );

uint8_t Send_K210msgBCC(const struct Send_K210msg* msg) //针对性的BCC校验函数
{
    uint8_t bcc = 0;
    const uint8_t* data = (const uint8_t*)msg;
    for (size_t i = 0; i < sizeof(struct Send_K210msg) - 2; i++) {
        bcc ^= data[i];
    }
    return bcc;
}

void update_sendmsg_and_Send(uint8_t keyvalue)//更新数据并发送
{
	send_k210msg.Head = 0xAF;
	send_k210msg.End = 0xFA;
	send_k210msg.select_color = keyvalue;
	send_k210msg.BCCcheck = Send_K210msgBCC(&send_k210msg);
	
	uint8_t* sendptr = (uint8_t*)&send_k210msg;
	for(uint8_t i =0;i<send_len;i++)
	{
		usart3_send(*sendptr);
		sendptr++;
	}
}

/////////// 定义向k210传输数据的数组 END ///////////////////


/**************************************************************************
函数功能：串口3发送数据
入口参数：无
返 回 值：无
**************************************************************************/
void usart3_send(u8 data)
{
    USART3->DR = data;
    while((USART3->SR&0x40)==0);
}


// 通用 BCC校验和的函数
unsigned char calculateBCC(const unsigned char *data, u16 length) {
    unsigned char bcc = 0;
	u16 i =0;
    for (i = 0; i < length; i++) {
        bcc ^= data[i];
    }
    return bcc;
}

struct K210_Recvmsg k210_recv; //定义接收数据的数据组

OBJECT_TRACK_t ObjectTrack;

uint8_t num_flag = 0,show_num = 0;

void K210_data_callback(u8 recv)
{
	static u8 recvlen = sizeof(k210_recv);//计算要接收的数据大小
	static u8 recv_data[sizeof(k210_recv)];//用于存放接收数据的数组
	static u8 recv_counts=0;//接收到的数据计数值
	
	recv_data[recv_counts] = recv;
	
    if( recv==K210_HEAD || recv_counts>0) //检查帧头是否正确
        recv_counts++;
    else
        recv_counts=0;
	
    if( recv_counts==recvlen )//接收到满足数据长度的数据
    {	
        recv_counts=0;//清空计数值,以便下次使用
        if( recv_data[recvlen-1]== K210_END ) //检查帧尾是否正确
        {		
            //检查BCC校验值是否正确
            if( recv_data[recvlen-2]==calculateBCC(recv_data,recvlen-2) )
            {
                //数据被正确接收后,开始自动解包
                u8 *recvptr = (u8*)&k210_recv;
                for(u8 i=0;i<recvlen;i++)
                {
                    *recvptr = recv_data[i];
                    recvptr++;
                }
				
				/////数据解包完成,下面可以开始使用接受到的数据/////////
				
				if( k210_recv.Cam_W==0xEF &&  k210_recv.Cam_H == 0xFE) //数值识别demo
				{
					num_flag = 1;
					show_num = k210_recv.follow_x;//识别到的数字
				}
				else //常规跟随功能
				{
					ObjectTrack.cam_centerX = (float)k210_recv.Cam_W/2.0f;
					ObjectTrack.cam_centerY = (float)k210_recv.Cam_H/2.0f;
						
					ObjectTrack.centerX = (float)k210_recv.follow_x;
					ObjectTrack.centerY = (float)k210_recv.follow_y;
					
					ObjectTrack.count_Outline = 0;
					ObjectTrack.lost=0;
				}

				
            }
        }

    }
	
	
}


/**************************************************************************
函数功能：串口2中断服务函数
入口参数：无
返回  值：无
**************************************************************************/
void USART3_IRQHandler(void)
{
    if(USART_GetITStatus(USART3, USART_IT_RXNE)) //接收到数据
    {

		K210_data_callback(USART3->DR);
    }
}

/**************************************************************************
函数功能：串口3发送数据函数
入口参数：舵机A角度，舵机B角度
返回  值：无
**************************************************************************/
void usart3_sendAngleBlock(int Angle_A, int Angle_B)
{
    int  BlockCheck=0;

    BlockCheck=Angle_A^BlockCheck;
    BlockCheck=Angle_B^BlockCheck; //异或求校验位

    usart3_send(0xff);       //帧头
    usart3_send(0xfe);       //帧头
    usart3_send(Angle_A);    //舵机A角度
    usart3_send(Angle_B);    //舵机B角度
    usart3_send(0);
    usart3_send(0);
    usart3_send(0);
    usart3_send(0);
    usart3_send(0);
    usart3_send(BlockCheck);    //BBC校验位
}
