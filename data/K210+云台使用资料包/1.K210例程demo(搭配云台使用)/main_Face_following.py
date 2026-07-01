import sensor, image, time, lcd
from maix import KPU
import gc

from WHEELTEC_PackSerial import Uart_SendPack
from collections import OrderedDict

from board import board_info
from fpioa_manager import fm
from machine import UART
"""
模块说明：
# sensor 摄像头控制
# image  图像处理
# lcd    LCD显示
# KPU    加速
# gc     垃圾回收
"""

# 定义需要向单片机传输的数据
pack1_msg = OrderedDict([
    ('Head',0xCC),     # 帧头u8
    ('Cam_W', 320),     # 屏幕像素宽
    ('Cam_H', 240),      # 屏幕像素高
    ('follow_x',0),      # 人脸中心坐标x
    ('follow_y',0),      # 人脸中心坐标y
    ('BCCcheck',0),    # BCC校验位 u8
    ('End',0xDD)       # 帧尾  u8
])
pack1_format = '<B4H2B'

# 实例化数据打包的对象
pack1 = Uart_SendPack(pack1_msg,pack1_format)

# 更新数据包数据
def update_pack1_data(follow_x,follow_y):
    global pack1
    pack1.msg["follow_x"] = follow_x
    pack1.msg["follow_y"] = follow_y
    pack1.msg["BCCcheck"] = pack1.pack_BCC_Value()
    return pack1.get_Pack_List()

# 引脚映射
fm.register(1, fm.fpioa.UART1_RX)
fm.register(0, fm.fpioa.UART1_TX)

# 构造UART对象
uart1 = UART(UART.UART1, 9600)


# LCD初始化
lcd.init()


"""
# 摄像头初始化
1.相机复位
2.设置图像格式RGB565
3.设置分辨率320x240
4.跳过1000帧数据,等待摄像头设置生效
"""
sensor.reset(dual_buff=True)
sensor.reset(freq=24000000, dual_buff=1)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_auto_gain(True)      # 自动增益设置
sensor.set_auto_whitebal(False) # 自动白平衡设置
sensor.skip_frames(time = 1000)

# 创建时钟对象,用于计算帧率FPS
clock = time.clock()

# 描点数组,用于YOLO V2目标检测算法
anchor = (0.1075, 0.126875, 0.126875, 0.175, 0.1465625, 0.2246875,\
          0.1953125, 0.25375, 0.2440625, 0.351875, 0.341875, 0.4721875, \
          0.5078125, 0.6696875, 0.8984375, 1.099687, 2.129062, 2.425937)

# 创建KPU对象,加载训练模型(人脸识别),初始化YOLO V2目标检测
kpu = KPU()
kpu.load_kmodel("/sd/KPU/yolo_face_detect/face_detect_320x240.kmodel")
kpu.init_yolo2(anchor, anchor_num=9, img_w=320, img_h=240, net_w=320 , net_h=240 , \
               layer_w=10 ,layer_h=8, threshold=0.5, nms_value=0.2, classes=1)


# 主任务
while 1:

    # 垃圾回收
    gc.collect()

    # 时钟更新,用于FPS检测
    clock.tick()

    # 捕获一帧图像
    img = sensor.snapshot()

    # 对图像进行处理
    kpu.run_with_output(img)

    # 获取检测结果
    dect = kpu.regionlayer_yolo2()

    # 获取FPS
    fps = clock.fps()

    # 检测到人脸
    if len(dect) > 0:

        # showlist = []
        # for i in sendlist:
        #     showlist.append(hex(i))
        # print(showlist)

        # 找到最大的人脸
        max_face = dect[0]
        for l in dect :
            if l[2]*l[3] > max_face[2]*max_face[3]:
                max_face = l

        # 将最大的人脸框选出来
        a = img.draw_rectangle(max_face[0],max_face[1],max_face[2],max_face[3], color=(0, 255, 0))

        cen_x = max_face[0]+int(max_face[2]/2)
        cen_y = max_face[1]+int(max_face[3]/2)
        img.draw_cross(cen_x,cen_y,color=(0,255,0),scale=4)
    else:
        cen_x = int(pack1.msg["Cam_W"]/2)
        cen_y = int(pack1.msg["Cam_H"]/2)

    # 将识别到最大的人脸中心坐标发送到stm32
    sendlist = update_pack1_data(cen_x,cen_y)
    uart1.write(sendlist)

    a = img.draw_string(0, 0, "%2.1ffps" %(fps), color=(0, 60, 255), scale=2.0)
    img.draw_string(0,220,"FaceTrack",color=(255,0,0),scale=2.0)
    img.draw_cross(160,120,color=(255,0,0),scale=4)
    lcd.display(img)

kpu.deinit()
