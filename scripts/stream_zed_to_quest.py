"""
ZED Mini → Quest 画面串流 (简化版, 无需机器人)
Stream ZED Mini stereo video directly to Quest VR headset
"""

import sys
sys.path.append("teleop/")

import numpy as np
import time
import cv2
from constants_vuer import *
from TeleVision import OpenTeleVision
import pyzed.sl as sl
from multiprocessing import Array, Process, shared_memory, Queue, Manager, Event, Semaphore

resolution = (720, 1280)
crop_size_w = 340  # 原教程参数
crop_size_h = 0
resolution_cropped = (resolution[0] - crop_size_h, resolution[1] - 2 * crop_size_w)  # (720, 1280)

# Create a Camera object
zed = sl.Camera()

# Create a InitParameters object and set configuration parameters
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD720
init_params.camera_fps = 60  # 原教程 60fps

# Open the camera
err = zed.open(init_params)
if err != sl.ERROR_CODE.SUCCESS:
    print("Camera Open : " + repr(err) + ". Exit program.")
    exit()

print("ZED Mini opened successfully!")
print(f"Resolution: {resolution_cropped}")

i = 0
image_left = sl.Mat()
image_right = sl.Mat()
runtime_parameters = sl.RuntimeParameters()

img_shape = (resolution_cropped[0], 2 * resolution_cropped[1], 3)
img_height, img_width = resolution_cropped[:2]
shm = shared_memory.SharedMemory(create=True, size=np.prod(img_shape) * np.uint8().itemsize)
img_array = np.ndarray((img_shape[0], img_shape[1], 3), dtype=np.uint8, buffer=shm.buf)
image_queue = Queue()
toggle_streaming = Event()
tv = OpenTeleVision(resolution_cropped, shm.name, image_queue, toggle_streaming, stream_mode="image", ngrok=True)

print("\n" + "=" * 60)
print("  Server started! Open in Quest browser:")
print(f"  https://192.168.3.3:8012")
print("=" * 60 + "\n")

while True:
    start = time.time()

    if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
        zed.retrieve_image(image_left, sl.VIEW.LEFT)
        zed.retrieve_image(image_right, sl.VIEW.RIGHT)

    left_img = image_left.numpy()
    right_img = image_right.numpy()

    # 裁剪（兼容 crop_size=0 的情况）
    if crop_size_w > 0:
        left_img = left_img[crop_size_h:, crop_size_w:-crop_size_w]
        right_img = right_img[crop_size_h:, crop_size_w:-crop_size_w]
    else:
        left_img = left_img[crop_size_h:]
        right_img = right_img[crop_size_h:]

    bgr = np.hstack((left_img, right_img))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGRA2RGB)

    np.copyto(img_array, rgb)
    image_queue.put(rgb)  # for WebRTC

    end = time.time()
    fps = 1/(end-start)
    if i % 30 == 0:
        print(f"\rStreaming FPS: {fps:.1f}", end="")
    i += 1

zed.close()
