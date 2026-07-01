import sensor, image, time, lcd

from board import board_info
from maix import GPIO
from fpioa_manager import fm
from machine import UART

# 导入数据打包和解析类方法
from WHEELTEC_PackSerial import Uart_SendPack
from collections import OrderedDict # 用于创建有序字典

fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
key=GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_NONE)

lcd.init()
sensor.reset()
sensor.reset(freq=24000000, dual_buff=1)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_auto_gain(False)      # 颜色跟踪必须关闭自动增益
sensor.set_auto_whitebal(False)  # 颜色跟踪必须关闭白平衡
sensor.skip_frames(time = 1000) # 跳过1000帧等待稳定
clock = time.clock()

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

# 指定串口引脚并构造UART对象,用于与stm32通信
fm.register(1, fm.fpioa.UART1_RX)
fm.register(0, fm.fpioa.UART1_TX)
uart1 = UART(UART.UART1, 9600)


# 学习方框大小,根据实际效果调整到最佳即可
learn_box_size = 50
r = [(320//2)-(learn_box_size//2), (240//2)-(learn_box_size//2), learn_box_size, learn_box_size]

# 等待用户按下按键开始学习
while True:
    img = sensor.snapshot()
    img.draw_rectangle(r)
    img.draw_string(0,0,"Press the BOOT button \r\n to start learning",color=(255, 60, 0), scale=2.0)
    img.draw_string(r[0],r[1]+r[3],"Learing box",scale=2.0)
    lcd.display(img)
    if key.value()==0:
        break


# 用户按下按键后,开始学习方块内的阈值
threshold = [50, 50, 0, 0, 0, 0]

# 学习的次数
learn_times = 200

for i in range(learn_times):

    while True:
        img = sensor.snapshot()
        if img != None:
            break

    hist = img.get_histogram(roi=r) # 学习方框r的阈值
    lo = hist.get_percentile(0.01) # 直方图配置
    hi = hist.get_percentile(0.99)


    # 对阈值逐渐平滑更新
    threshold[0] = (threshold[0] + lo.l_value()) // 2
    threshold[1] = (threshold[1] + hi.l_value()) // 2
    threshold[2] = (threshold[2] + lo.a_value()) // 2
    threshold[3] = (threshold[3] + hi.a_value()) // 2
    threshold[4] = (threshold[4] + lo.b_value()) // 2
    threshold[5] = (threshold[5] + hi.b_value()) // 2

    # 学习中提示
    sch = (float)(i/learn_times)*100
    img.draw_string(0,0,"Please keep the camera \r\nsteady during learning...%d%%"%sch,color=(255, 60, 0), scale=2.0)

    # 对满足阈值的物体画红框
    img.draw_rectangle(r) # 白框为学习框
    for blob in img.find_blobs([threshold], pixels_threshold=100, area_threshold=100, merge=True, margin=10):
        img.draw_rectangle(blob.rect(),color=(255, 0, 0), scale=2.0) # 红框为学习到的阈值识别框

    # 显示图像在lcd
    lcd.display(img)

# 学习完毕
print("learn over!!!!!")
print("threshold lsit:",threshold)

#开始跟踪学习后的物体
while True:
    clock.tick()
    img = sensor.snapshot()

    max_blob = None
    cen_x = int(send_pack1.msg["Cam_W"]/2)
    cen_y = int(send_pack1.msg["Cam_H"]/2)

    blobs = img.find_blobs([threshold], pixels_threshold=100, area_threshold=100, merge=True, margin=10)

    # 找到视角范围内最大面积的物体进行追踪
    if blobs:
        max_blob = blobs[0]
        for blob in blobs:
            if blob.rect()[2]*blob.rect()[3] > max_blob.rect()[2]*max_blob.rect()[3]:
                max_blob = blob

        cen_x = max_blob.cx()
        cen_y = max_blob.cy()
        img.draw_rectangle(max_blob.rect(),color=(255, 0, 0))
        img.draw_cross(cen_x, cen_y,color=(255, 0, 0))

    send_to_32 = update_sendpack1_data(cen_x,cen_y)
    uart1.write(send_to_32)

    # fps显示
    fps = clock.fps()
    img.draw_string(0, 0, "%2.1fps" %(fps), color=(0, 60, 255), scale=2.0)
    img.draw_string(0,220,"threshold: "+str(threshold),scale=1.5)
    lcd.display(img)
