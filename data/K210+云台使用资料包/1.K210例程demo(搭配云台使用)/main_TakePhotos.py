from board import board_info
from fpioa_manager import fm
from maix import GPIO
import time

import sensor
import lcd
import image


# 屏幕与相机初始化
lcd.init()
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 1000)
print("cam init ok")

# 获取图像保存路径
save_num = 0
def get_imgpath(imgNum):
    return  "/sd/image"+str(imgNum)+".jpg"

# 按键初始化
fm.register(board_info.USER_LED, fm.fpioa.GPIOHS1, force=True)
led = GPIO(GPIO.GPIOHS1, GPIO.OUT)


# 注册按键和回调函数
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
key=GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_NONE)


onceflag = 1
while True:
    img = sensor.snapshot()
    lcd.display(img)

    if key.value() == 0 and onceflag == 1:
        print("save img!")
        lcd.clear(lcd.WHITE)
        img = sensor.snapshot()
        lcd.clear()
        img.save( get_imgpath(save_num) )
        save_num = save_num + 1
        onceflag = 0
    elif key.value() == 1 and onceflag == 0:
        onceflag = 1


key.disirq()
fm.unregister(board_info.BOOT_KEY)
