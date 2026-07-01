import sensor, image, time, lcd
from maix import KPU
import gc
from fpioa_manager import fm
from machine import UART

# 导入数据打包和解析类方法
from WHEELTEC_PackSerial import Uart_SendPack
from collections import OrderedDict # 用于创建有序字典

""" 创建需要往stm32端发送数据的数据包 """
# 需要发送的数据(如果需要增删数据,则修改此处以及修改数据格式,同时在32端也对应增删即可)
send_pack1_msg = OrderedDict([
        ('Head',0xCC),  # 帧头           uint8_t类型
        ('Cam_W', 0xEF), # 使用特征码告知stm32这是数字识别demo
        ('Cam_H', 0xFE), # 使用特征码告知stm32这是数字识别demo
        ('num',0),       # 用于存放识别到的数字
        ('follow_y',0),  # 预留
        ('BccCheck',0), #
        ('End',0xDD)    # 帧尾            uint8_t类型
])

# 数据格式 <代表小端模式, B代表uint8_t类型,4H代表4个uint16_t类型,2B代表2个uint8_t类型
send_pack1_format = "<B4H2B"

#实例化数据打包对象
send_pack1 = Uart_SendPack(send_pack1_msg,send_pack1_format)

# 更新需要发送的数据并返回打包结果,将结果直接发送到stm32端即可
def update_sendpack1_data(num):
    global send_pack1
    send_pack1.msg['num'] = num
    send_pack1.msg['BccCheck'] = send_pack1.pack_BCC_Value()
    return send_pack1.get_Pack_List()
""" 创建需要往stm32端发送数据的数据包 END """

# 指定串口引脚并构造UART对象
fm.register(1, fm.fpioa.UART1_RX)
fm.register(0, fm.fpioa.UART1_TX)
uart1 = UART(UART.UART1, 9600)

lcd.init(freq=15000000)
sensor.reset(dual_buff=True)        # Reset and initialize the sensor. It will
                                    # run automatically, call sensor.run(0) to stop
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
sensor.set_windowing((224, 224))
sensor.skip_frames(time = 1000)     # Wait for settings take effect.
clock = time.clock()                # Create a clock object to track the FPS.

kpu = KPU()
kpu.load_kmodel("/sd/KPU/mnist/uint8_mnist_cnn_model.kmodel")

while True:
    gc.collect()
    img = sensor.snapshot()
    img_mnist1=img.to_grayscale(1)        #convert to gray
    img_mnist2=img_mnist1.resize(112,112)
    a=img_mnist2.invert()                 #invert picture as mnist need
    a=img_mnist2.strech_char(1)           #preprocessing pictures, eliminate dark corner
    a=img_mnist2.pix_to_ai()

    out = kpu.run_with_output(img_mnist2, getlist=True)
    max_mnist = max(out)
    index_mnist = out.index(max_mnist)
    #score = KPU.sigmoid(max_mnist)
    display_str = "num: %d" % index_mnist
    print(display_str)

    # 将识别结果发送到stm32
    sendlist = update_sendpack1_data(index_mnist)
    uart1.write(sendlist)

    a=img.draw_string(4,3,display_str,color=(0,0,0),scale=2)
    lcd.display(img)

kpu.deinit()


