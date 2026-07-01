"""
ZED Mini → Pico 高清串流 (无降采样, 全视野)
"""
import sys
sys.path.append("teleop/")

import numpy as np
import time
import cv2
from constants_vuer import *
from TeleVisionHD import OpenTeleVision
import pyzed.sl as sl
from multiprocessing import Array, Process, shared_memory, Queue, Manager, Event, Semaphore

# 保留裁剪（去除畸变边缘），但不降采样
crop_size_w = 200
crop_size_h = 0
resolution_cropped = (720 - crop_size_h, 1280 - 2 * crop_size_w)  # (720, 880)

# 打开 ZED
zed = sl.Camera()
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD720
init_params.camera_fps = 60
err = zed.open(init_params)
if err != sl.ERROR_CODE.SUCCESS:
    print("Camera Open : " + repr(err) + ". Exit program.")
    exit()

print("ZED Mini opened successfully!")
print(f"Resolution per eye: {resolution_cropped}")

image_left = sl.Mat()
image_right = sl.Mat()
runtime_parameters = sl.RuntimeParameters()

# 共享内存 + 队列
img_shape = (resolution_cropped[0], 2 * resolution_cropped[1], 3)
shm = shared_memory.SharedMemory(create=True, size=np.prod(img_shape) * np.uint8().itemsize)
img_array = np.ndarray((img_shape[0], img_shape[1], 3), dtype=np.uint8, buffer=shm.buf)
image_queue = Queue()
toggle_streaming = Event()

# 清空共享内存，防止垃圾画面闪烁
img_array[:] = 0

# 启动 OpenTeleVisionHD（无降采样, quality=95）
tv = OpenTeleVision(resolution_cropped, shm.name, image_queue, toggle_streaming, stream_mode="image", ngrok=True)

print("\n" + "=" * 60)
print("  Server started! Open in Pico browser:")
print("  http://127.0.0.1:8012")
print("=" * 60 + "\n")

i = 0
while True:
    start = time.time()

    if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
        zed.retrieve_image(image_left, sl.VIEW.LEFT)
        zed.retrieve_image(image_right, sl.VIEW.RIGHT)

    left_img = image_left.numpy()
    right_img = image_right.numpy()

    # 裁剪（为 0 时取全部）
    if crop_size_w > 0:
        left_img = left_img[crop_size_h:, crop_size_w:-crop_size_w]
        right_img = right_img[crop_size_h:, crop_size_w:-crop_size_w]
    else:
        left_img = left_img[crop_size_h:]
        right_img = right_img[crop_size_h:]

    bgr = np.hstack((left_img, right_img))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGRA2RGB)
    np.copyto(img_array, rgb)

    if i % 30 == 0:
        print(f"\rStreaming FPS: {1/(time.time()-start):.1f}", end="")
    i += 1

zed.close()
