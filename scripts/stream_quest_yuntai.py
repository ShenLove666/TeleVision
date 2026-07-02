"""
ZED Mini → Quest 画面串流 + 云台头部跟随
基于 stream_zed_to_quest.py 加入云台控制
"""

import sys
sys.path.append("teleop/")

import numpy as np
import time
import cv2
import serial
from constants_vuer import grd_yup2grd_zup
from TeleVisionHD import OpenTeleVision
import pyzed.sl as sl
from multiprocessing import shared_memory, Queue, Event
from pytransform3d import rotations

# ============================================================
# 参数
# ============================================================

# 串口
SERIAL_PORT = '/dev/ttyACM0'
SERIAL_BAUD = 115200

# ZED
resolution = (720, 1280)
crop_size_w = 340
crop_size_h = 0
resolution_cropped = (resolution[0] - crop_size_h, resolution[1] - 2 * crop_size_w)

# 舵机映射
SERVO_BOTTOM_MIN = 0
SERVO_BOTTOM_MAX = 270
SERVO_BOTTOM_CENTER = 135

SERVO_TOP_MIN = 0
SERVO_TOP_MAX = 180
SERVO_TOP_CENTER = 90

YAW_RANGE_DEG = 90
PITCH_RANGE_DEG = 60

SMOOTHING = 0.3
DEAD_ZONE_DEG = 0.5

# 舵机更新频率上限 (Hz) — 舵机不需要 60fps，30Hz 足够平滑
SERVO_UPDATE_HZ = 30

# ============================================================
# 云台控制
# ============================================================

class YunTai:
    def __init__(self, port, baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self._last_b = -1
        self._last_t = -1

    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"[云台] {self.port} @ {self.baud}")
            return True
        except Exception as e:
            print(f"[云台] 打开失败: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    @property
    def connected(self):
        return self.ser is not None and self.ser.is_open

    def send(self, b_angle, t_angle):
        b = max(0, min(270, int(round(b_angle))))
        t = max(0, min(180, int(round(t_angle))))
        if b == self._last_b and t == self._last_t:
            return
        self._last_b, self._last_t = b, t
        parity = b ^ t
        self.ser.write(bytes([0xFF, 0xFE, b, t, 0, 0, 0, 0, 0, parity]))

    def center(self):
        self._last_b = -1
        self._last_t = -1
        self.send(SERVO_BOTTOM_CENTER, SERVO_TOP_CENTER)


# ============================================================
# 角度映射
# ============================================================

def yaw2servo(deg):
    n = np.clip(deg / YAW_RANGE_DEG, -1, 1)
    if n < 0:
        return SERVO_BOTTOM_CENTER + n * (SERVO_BOTTOM_CENTER - SERVO_BOTTOM_MIN)
    else:
        return SERVO_BOTTOM_CENTER + n * (SERVO_BOTTOM_MAX - SERVO_BOTTOM_CENTER)

def pitch2servo(deg):
    n = np.clip(deg / PITCH_RANGE_DEG, -1, 1)
    if n < 0:
        return SERVO_TOP_CENTER + n * (SERVO_TOP_CENTER - SERVO_TOP_MIN)
    else:
        return SERVO_TOP_CENTER + n * (SERVO_TOP_MAX - SERVO_TOP_CENTER)


# ============================================================
# 主程序
# ============================================================

print("=" * 60)
print("  ZED Mini → Quest 串流 + 云台头部跟随")
print("=" * 60)

yuntai = YunTai(SERIAL_PORT, SERIAL_BAUD)
if yuntai.open():
    yuntai.center()
    time.sleep(0.3)
else:
    print("  继续运行(仅串流)")

zed = sl.Camera()
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD720
init_params.camera_fps = 60
err = zed.open(init_params)
if err != sl.ERROR_CODE.SUCCESS:
    print("Camera Open : " + repr(err) + ". Exit program.")
    yuntai.close()
    exit()

print(f"Resolution: {resolution_cropped}")

image_left = sl.Mat()
image_right = sl.Mat()
runtime_parameters = sl.RuntimeParameters()

img_shape = (resolution_cropped[0], 2 * resolution_cropped[1], 3)
shm = shared_memory.SharedMemory(create=True, size=np.prod(img_shape) * np.uint8().itemsize)
img_array = np.ndarray((img_shape[0], img_shape[1], 3), dtype=np.uint8, buffer=shm.buf)
image_queue = Queue()
toggle_streaming = Event()
tv = OpenTeleVision(resolution_cropped, shm.name, image_queue, toggle_streaming,
                    stream_mode="image", ngrok=True)

print("\n" + "=" * 60)
print("  Server started! Open in Quest browser:")
print("  https://192.168.3.3:8012   (或 ngrok 地址)")
print("=" * 60 + "\n")

smooth_yaw = 0.0
smooth_pitch = 0.0
i = 0
last_servo_time = 0
servo_interval = 1.0 / SERVO_UPDATE_HZ

try:
    while True:
        loop_start = time.time()

        # --- 头部追踪 → 云台 (限频 SERVO_UPDATE_HZ) ---
        if yuntai.connected and (loop_start - last_servo_time) >= servo_interval:
            last_servo_time = loop_start
            head_mat = grd_yup2grd_zup[:3, :3] @ tv.head_matrix[:3, :3] @ grd_yup2grd_zup[:3, :3].T
            if np.sum(head_mat) == 0:
                head_mat = np.eye(3)
            try:
                q = rotations.quaternion_from_matrix(head_mat[:3, :3])
                ypr = rotations.euler_from_quaternion(q, 2, 1, 0, False)
                ry = np.degrees(ypr[0])
                rp = np.degrees(ypr[1])

                if abs(ry) < DEAD_ZONE_DEG:
                    ry = 0
                if abs(rp) < DEAD_ZONE_DEG:
                    rp = 0

                smooth_yaw = smooth_yaw * (1 - SMOOTHING) + ry * SMOOTHING
                smooth_pitch = smooth_pitch * (1 - SMOOTHING) + rp * SMOOTHING

                sb = yaw2servo(smooth_yaw)
                st = pitch2servo(smooth_pitch)
                yuntai.send(sb, st)

                if i % 30 == 0:
                    print(f"  yaw={ry:+.0f}° pitch={rp:+.0f}° → servo({sb},{st})")
            except Exception:
                pass

        # --- ZED 采集 + 推流 ---
        if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_left, sl.VIEW.LEFT)
            zed.retrieve_image(image_right, sl.VIEW.RIGHT)

        left_img = image_left.numpy()
        right_img = image_right.numpy()

        if crop_size_w > 0:
            left_img = left_img[crop_size_h:, crop_size_w:-crop_size_w]
            right_img = right_img[crop_size_h:, crop_size_w:-crop_size_w]
        else:
            left_img = left_img[crop_size_h:]
            right_img = right_img[crop_size_h:]

        bgr = np.hstack((left_img, right_img))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGRA2RGB)

        np.copyto(img_array, rgb)
        # 注意: image 模式下不需要 queue.put()，vuer 直接从共享内存读
        # image_queue 是给 WebRTC 模式用的

        if i % 30 == 0:
            print(f"\rStreaming FPS: {1/(time.time()-loop_start):.1f}", end="")
        i += 1

        # 保底限速：即使 zed.grab 不阻塞 (丢帧等)，也不让循环空转
        elapsed = time.time() - loop_start
        min_loop_time = 1.0 / 120  # 最高 120Hz
        if elapsed < min_loop_time:
            time.sleep(min_loop_time - elapsed)

except KeyboardInterrupt:
    print("\n\n[退出] 用户中断")
except Exception as e:
    print(f"\n[错误] {e}")
    import traceback
    traceback.print_exc()
finally:
    print("[清理]...")
    if yuntai.connected:
        yuntai.center()
        time.sleep(0.3)
        yuntai.close()
    zed.close()
    shm.unlink()
    print("[完成]")
