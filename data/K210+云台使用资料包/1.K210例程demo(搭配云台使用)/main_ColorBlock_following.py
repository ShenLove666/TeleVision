import sensor , image , time , lcd
from fpioa_manager import fm
from machine import UART

from board import board_info
from maix import GPIO

# 导入数据打包和解析类方法
from WHEELTEC_PackSerial import Uart_RecvPack
from WHEELTEC_PackSerial import Uart_SendPack
from collections import OrderedDict # 用于创建有序字典


""" 创建需要往stm32端发送数据的数据包 """
# 需要发送的数据(如果需要增删数据,则修改此处以及修改数据格式,同时在32端也对应增删即可)
send_pack1_msg = OrderedDict([
        ('Head',0xCC),  # 帧头           uint8_t类型
        ('Cam_W', 320), # 相机的像素宽度  uint16_t 类型
        ('Cam_H', 240), # 相机的像素长度  uint16_t 类型
        ('follow_x',0),  # 需要跟踪的点x   uint16_t 类型
        ('follow_y',0),  # 需要跟踪的点y   uint16_t 类型
        ('BccCheck',0), # 数据BCC校验位   uint8_t类型
        ('End',0xDD)    # 帧尾            uint8_t类型
])

# 数据格式 <代表小端模式, B代表uint8_t类型,4H代表4个uint16_t类型,2B代表2个uint8_t类型
send_pack1_format = "<B4H2B"

#实例化数据打包对象
send_pack1 = Uart_SendPack(send_pack1_msg,send_pack1_format)

# 更新需要发送的数据并返回打包结果,将结果直接发送到stm32端即可
def update_sendpack1_data(follow_x,follow_y):
    global send_pack1
    send_pack1.msg['follow_x'] = follow_x
    send_pack1.msg['follow_y'] = follow_y
    send_pack1.msg['BccCheck'] = send_pack1.pack_BCC_Value()
    return send_pack1.get_Pack_List()
""" 创建需要往stm32端发送数据的数据包 END """


""" 创建需要接收stm32端数据的数据包 """
# (如果需要增删数据,则修改此处以及修改数据格式,同时在32端也对应增删即可)
recv_pack1_msg = OrderedDict([
        ('Head',0xAF),        # 帧头
        ('seltec_color', 0),  # stm32需要追踪的颜色
        ('BccCheck',0),       # BCC校验
        ('End',0xFA)          # 帧尾
])
recv_pack1_format = "<4B"
recv_pack1 = Uart_RecvPack(recv_pack1_msg,recv_pack1_format)
""" 创建需要接收stm32端数据的数据包 END """


# 各传感器初始化
lcd.init()
sensor.reset()
sensor.reset(freq=24000000, dual_buff=1)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)

sensor.set_auto_gain(False)      # 颜色跟踪必须关闭自动增益
sensor.set_auto_whitebal(False)  # 颜色跟踪必须关闭白平衡

sensor.skip_frames(time = 1000)

#帧率时钟
clock = time.clock()

# 指定串口引脚并构造UART对象
fm.register(1, fm.fpioa.UART1_RX)
fm.register(0, fm.fpioa.UART1_TX)
uart1 = UART(UART.UART1, 9600)

color_thresholds = [
    (20, 68, 0, 47, -62, -35), # 蓝
    (14, 62, -38, -1, -3, 26), # 绿
    (43, 92,-2, 20, 48, 70),   # 黄
    (18,62,39,84,23,45),       # 红
]

# 颜色字符串与上面字符一一对应
color_strings = ['Blue','Green','Yellow','Red']

# 追踪的颜色选择
cmd_color = 0

# 辅组接收数据的变量
Last_recv32 = None

# tmp:设置一个按键,用于切换颜色
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
key=GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_NONE)

onceflag = 1

while True:

    # 按键扫描
    if key.value() == 0 and onceflag == 1:
        cmd_color = cmd_color + 1
        if cmd_color > len(color_strings)-1:
           cmd_color = 0
        onceflag = 0
    elif key.value() == 1 and onceflag == 0:
        onceflag = 1

    # 接收到stm32串口数据
    if uart1.any()!=0:
        recv_from_32 = ord(uart1.read(1)) # 将读取到的bytes字节数据,使用ord方法转成10进制数
        # 读取到帧头与上一帧数据的帧尾,说明是正确数据(注意：此方法接收数据会丢失最开始的一帧数据,后续所有数据都正常)
        if recv_from_32 == recv_pack1.msg["Head"] and Last_recv32 == recv_pack1.msg["End"]:

            recv_from_32 = bytes([recv_from_32]) # 恢复第一字节数据成bytes类型,并与下面读取到的数据相加得到一帧完整的数据
            recv_from_32 += uart1.read(recv_pack1.data_len-1)

            # 将接收到的一帧完整数据送入解包方法,进行数据解包
            if recv_pack1.unpack_value(recv_from_32) == True:

                # 判断接收到的目标颜色是否超出索引值
                if recv_pack1.msg["seltec_color"] > len(color_strings)-1:
                    print("out of index")
                else:
                    cmd_color = recv_pack1.msg["seltec_color"]
                    print( "Now Tracked :"+ color_strings[cmd_color] )

            # 解包完毕,保存最后一帧数据方便下次解包使用
            recv_from_32 = recv_from_32[recv_pack1.data_len-1]

        # 保存上一帧数据,用于辅组接收数据判断
        Last_recv32 = recv_from_32


    #用于计算帧率的函数，这里表示开始计时
    clock.tick()

    try:
        #从传感器捕获一张图像
        img = sensor.snapshot()
        blobs = img.find_blobs([color_thresholds[cmd_color]], pixels_threshold=100, area_threshold=100, merge=True, margin=10)

        max_blob = None
        cen_x = int(send_pack1.msg["Cam_W"]/2)
        cen_y = int(send_pack1.msg["Cam_H"]/2)

        if blobs:
            max_blob = blobs[0]
            for blob in blobs:
                # 找到面积最大的物体
                if blob.rect()[2]*blob.rect()[3] > max_blob.rect()[2]*blob.rect()[3]:
                    max_blob = blob

            # 框选出最大的物体
            cen_x = max_blob.cx()
            cen_y = max_blob.cy()
            img.draw_rectangle(max_blob.rect(), color=(255 , 0,0),thickness = 3)
            img.draw_cross(cen_x, cen_y, color=(255 , 0,0))


        # 将最大物体的中心坐标发送到stm32
        send_to_32 = update_sendpack1_data(cen_x,cen_y)
        uart1.write(send_to_32)

        fps = clock.fps()
        img.draw_string(0, 0, "%2.1fps" %(fps), color=(0, 60, 255), scale=2.0)
        img.draw_string(0,220,"Tracked: "+color_strings[cmd_color],color=(0,60, 255),scale=2.0)

        #显示在LCD上
        lcd.display(img)

    except Exception as e:
        print(e)
