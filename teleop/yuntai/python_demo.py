import time
import serial

# 串口参数
# 根据电脑的串口ID设置串口名称，COM为Windows上的串口号，Linux上可能是'/dev/ttyUSB0'
# 初始化串口
port = '/dev/ttyACM0'  # 串口名称
baudrate = 115200  # 波特率
parity = 0

# angle_bottom： 云台舵机 ； angle_top： 摆臂舵机
# 在使用过程中只需修改这两个变量即可
angle_bottom = 1
angle_top = 1
count=0
# 创建串口对象
ser = serial.Serial(port, baudrate, timeout=1)

# 检查串口是否打开
if ser.is_open:
    angle = 150
    while True:
        # angle_bottom： 云台舵机 ； angle_top： 摆臂舵机
        # 在使用过程中只需修改这两个变量即可
        # 循环将两个舵机从0到90度转动
        angle_bottom = angle
        angle_top = angle
        count=count+1
        print("count: "+str(count))
        print("angle: "+str(angle))

        # BBC校验码
        parity = angle_bottom ^ parity
        parity = angle_top ^ parity

        # 将十六进制数据转换为字节串
        hex_data = [0xff, 0xfe, angle_bottom, angle_top, 0x00, 0x00, 0x00, 0x00, 0x00, parity]
        byte_data = bytes(hex_data)

        # 发送数据
        ser.write(byte_data)

        angle += 1
        if angle>180:
            angle = 1

        # 等待一段时间，确保数据发送完成
        time.sleep(0.05)

else:
    print("串口打开失败")
