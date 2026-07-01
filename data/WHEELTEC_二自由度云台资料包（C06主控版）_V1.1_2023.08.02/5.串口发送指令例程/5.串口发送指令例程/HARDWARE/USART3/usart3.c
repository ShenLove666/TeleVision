
#include "usart3.h"

 u8 mode_data[2];
 u8 six_data_stop[2]={0X59,0X59};  //停止数据样本
 u8 six_data_start[2]={0X58,0X58};  //启动数据样本

void usart3_send(u8 data)
{
	USART3->DR = data;
	while((USART3->SR&0x40)==0);	
}
void uart3_init(u32 pclk2,u32 bound)
{  	 
	float temp;
	u16 mantissa;
	u16 fraction;	   
	temp=(float)(pclk2*1000000)/(bound*16);//得到USARTDIV
	mantissa=temp;				 //得到整数部分
	fraction=(temp-mantissa)*16; //得到小数部分	 
  mantissa<<=4;
	mantissa+=fraction; 
	RCC->APB2ENR|=1<<3;   //使能PORTB口时钟  
	RCC->APB1ENR|=1<<18;  //使能串口3时钟 
	GPIOB->CRH&=0XFFFF00FF; 
	GPIOB->CRH|=0X00008B00;//IO状态设置
	GPIOB->ODR|=1<<10;	  
	RCC->APB1RSTR|=1<<18;   //复位串口3
	RCC->APB1RSTR&=~(1<<18);//停止复位	   	   
	//波特率设置
 	USART3->BRR=mantissa; // 波特率设置	 
	USART3->CR1|=0X200C;  //1位停止,无校验位.
	//使能接收中断
	USART3->CR1|=1<<8;    //PE中断使能
	USART3->CR1|=1<<5;    //接收缓冲区非空中断使能	    	
	MY_NVIC_Init(2,1,USART3_IRQn,2);//组2，最低优先级 
}
int USART3_IRQHandler(void)
{	
	if(USART3->SR&(1<<5))//接收到数据	
	{	  		
				u8 temp;
				static u8 count,last_data,last_last_data;
	LED=0;
				temp=USART3->DR;
				Show_Data_Mb=temp;
			
				   if(Usart_Flag==0)
						{	
						if(last_data==0xfe&&last_last_data==0xff) 
						Usart_Flag=1,count=0;	
						}
					 if(Usart_Flag==1)
						{	
							Urxbuf[count]=temp;     
							count++;                
							if(count==8) {Usart_Flag=0; memcpy(&rxbuf,&Urxbuf,sizeof(Urxbuf));}
						}
						last_last_data=last_data;
						last_data=temp;
   }
return 0;	
}

