"""
ZED Mini → Pico 高清串流 + 云台头部跟随
========================================
基于 stream_hd.py，加入 Pico 头部追踪控制云台舵机。

串口协议 (WHEELTEC 云台):
  0xFF 0xFE angle_bottom angle_top 0x00 0x00 0x00 0x00 0x00 parity

使用方式:
  mamba activate television
  cd ~/TeleVision && python scripts/stream_hd_yuntai.py
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
# 可调参数
# ============================================================

# --- 串口 ---
SERIAL_PORT = '/dev/ttyACM0'     # 根据实际修改
SERIAL_BAUD = 115200

# --- ZED ---
crop_size_w = 200
crop_size_h = 0
resolution_cropped = (720 - crop_size_h, 1280 - 2 * crop_size_w)  # (720, 880)

# --- 舵机角度映射 ---
# 下舵机 (pan/旋转) 0~270°, 上舵机 (tilt/俯仰) 0~180°
SERVO_BOTTOM_MIN = 0
SERVO_BOTTOM_MAX = 270
SERVO_BOTTOM_CENTER = 135    # 正前方角度

SERVO_TOP_MIN = 0
SERVO_TOP_MAX = 180
SERVO_TOP_CENTER = 90        # 水平时角度

# 头部角度映射范围
YAW_RANGE_DEG = 90           # ±90° → 下舵机全行程
PITCH_RANGE_DEG = 60         # ±60° → 上舵机全行程

# 平滑滤波
SMOOTHING = 0.3              # 0=无平滑, 1=完全跟随
DEAD_ZONE_DEG = 0.5          # 死区(度), 防抖动

# 打印
PRINT_FPS = True
PRINT_ANGLES = True
PRINT_ANGLE_INTERVAL = 30    # 每多少帧打印一次角度


# ============================================================
# 云台串口控制
# ============================================================

class YunTaiController:
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self._last_bottom = -1
        self._last_top = -1

    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"[云台] 串口已打开: {self.port} @ {self.baud}")
            return True
        except serial.SerialException as e:
            print(f"[云台] ❌ 串口打开失败: {e}")
            print(f"       尝试: sudo chmod 666 {self.port}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[云台] 串口已关闭")

    def send_angles(self, angle_bottom: int, angle_top: int):
        """angle_bottom: 0~270, angle_top: 0~180"""
        angle_bottom = max(SERVO_BOTTOM_MIN, min(SERVO_BOTTOM_MAX, int(round(angle_bottom))))
        angle_top = max(SERVO_TOP_MIN, min(SERVO_TOP_MAX, int(round(angle_top))))

        # 角度没变就不发，减少串口负担
        if angle_bottom == self._last_bottom and angle_top == self._last_top:
            return
        self._last_bottom = angle_bottom
        self._last_top = angle_top

        parity = angle_bottom ^ angle_top
        packet = [0xFF, 0xFE, angle_bottom, angle_top, 0x00, 0x00, 0x00, 0x00, 0x00, parity]
        try:
            self.ser.write(bytes(packet))
        except serial.SerialException as e:
            print(f"[云台] 发送失败: {e}")

    def center(self):
        self._last_bottom = -1
        self._last_top = -1
        self.send_angles(SERVO_BOTTOM_CENTER, SERVO_TOP_CENTER)


# ============================================================
# 角度映射
# ============================================================

def head_yaw_to_servo(yaw_deg: float) -> int:
    """头部 yaw → 下舵机 (pan): 负=左, 正=右"""
    norm = np.clip(yaw_deg / YAW_RANGE_DEG, -1.0, 1.0)
    if norm < 0:
        return int(SERVO_BOTTOM_CENTER + norm * (SERVO_BOTTOM_CENTER - SERVO_BOTTOM_MIN))
    else:
        return int(SERVO_BOTTOM_CENTER + norm * (SERVO_BOTTOM_MAX - SERVO_BOTTOM_CENTER))


def head_pitch_to_servo(pitch_deg: float) -> int:
    """头部 pitch → 上舵机 (tilt): 负=向下, 正=向上"""
    norm = np.clip(pitch_deg / PITCH_RANGE_DEG, -1.0, 1.0)
    if norm < 0:
        return int(SERVO_TOP_CENTER + norm * (SERVO_TOP_CENTER - SERVO_TOP_MIN))
    else:
        return int(SERVO_TOP_CENTER + norm * (SERVO_TOP_MAX - SERVO_TOP_CENTER))


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("  ZED Mini → Pico 高清串流 + 云台头部跟随")
    print("=" * 60)

    # ---- 1. 云台串口 ----
    yuntai = YunTaiController(SERIAL_PORT, SERIAL_BAUD)
    if not yuntai.open():
        print("继续运行(仅串流无云台)...")
    else:
        yuntai.center()
        time.sleep(0.3)

    # ---- 2. ZED Mini ----
    print("\n[ZED] 打开相机...")
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = 60
    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"[ZED] ❌ 打开失败: {repr(err)}")
        yuntai.close()
        return
    print(f"[ZED] 已打开, 裁剪后分辨率: {resolution_cropped}")

    # ---- 3. 共享内存 + Vuer 服务器 ----
    img_shape = (resolution_cropped[0], 2 * resolution_cropped[1], 3)
    shm = shared_memory.SharedMemory(create=True, size=np.prod(img_shape) * np.uint8().itemsize)
    img_array = np.ndarray((img_shape[0], img_shape[1], 3), dtype=np.uint8, buffer=shm.buf)
    image_queue = Queue()
    toggle_streaming = Event()

    # 清空黑屏, 防止启动时闪绿屏
    img_array[:] = 0

    tv = OpenTeleVision(resolution_cropped, shm.name, image_queue, toggle_streaming,
                        stream_mode="image", ngrok=True)

    time.sleep(2)

    print("\n" + "=" * 60)
    print("  服务器已启动!")
    print("  在 Pico 浏览器中打开: http://127.0.0.1:8012")
    print("  点 Enter VR → Allow")
    print("  头部转动 → 云台跟随")
    print("=" * 60 + "\n")

    # ---- 4. 主循环 ----
    image_left = sl.Mat()
    image_right = sl.Mat()
    runtime_parameters = sl.RuntimeParameters()

    smooth_yaw_deg = 0.0
    smooth_pitch_deg = 0.0

    frame_count = 0
    fps_timer = time.time()
    angle_fps_counter = 0

    print("[运行中] Ctrl+C 退出\n")

    try:
        while True:
            loop_start = time.time()

            # --- A. 头部追踪 → 云台 ---
            if yuntai.is_open():
                head_mat = grd_yup2grd_zup[:3, :3] @ tv.head_matrix[:3, :3] @ grd_yup2grd_zup[:3, :3].T
                if np.sum(head_mat) == 0:
                    head_mat = np.eye(3)

                try:
                    head_rot = rotations.quaternion_from_matrix(head_mat[0:3, 0:3])
                    ypr = rotations.euler_from_quaternion(head_rot, 2, 1, 0, False)
                    raw_yaw = np.degrees(ypr[0])
                    raw_pitch = np.degrees(ypr[1])

                    # 死区
                    if abs(raw_yaw) < DEAD_ZONE_DEG:
                        raw_yaw = 0
                    if abs(raw_pitch) < DEAD_ZONE_DEG:
                        raw_pitch = 0

                    # 平滑
                    smooth_yaw_deg = smooth_yaw_deg * (1 - SMOOTHING) + raw_yaw * SMOOTHING
                    smooth_pitch_deg = smooth_pitch_deg * (1 - SMOOTHING) + raw_pitch * SMOOTHING

                    # 映射并发送
                    servo_bottom = head_yaw_to_servo(smooth_yaw_deg)
                    servo_top = head_pitch_to_servo(smooth_pitch_deg)
                    yuntai.send_angles(servo_bottom, servo_top)

                    if PRINT_ANGLES and frame_count % PRINT_ANGLE_INTERVAL == 0:
                        print(f"  头部: yaw={raw_yaw:+.1f}° pitch={raw_pitch:+.1f}° "
                              f"→ 舵机: bottom={servo_bottom} top={servo_top}")

                except Exception:
                    pass  # 头部数据可能暂时无效

            # --- B. ZED 采集 + 推流 ---
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

            # --- C. FPS ---
            frame_count += 1
            if PRINT_FPS and frame_count % 30 == 0:
                elapsed = time.time() - fps_timer
                print(f"\r  FPS: {frame_count / elapsed:.1f}  ", end="")
                frame_count = 0
                fps_timer = time.time()

    except KeyboardInterrupt:
        print("\n\n[退出] 用户中断")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[清理] 复位云台...")
        if yuntai.is_open():
            yuntai.center()
            time.sleep(0.3)
            yuntai.close()
        zed.close()
        shm.unlink()
        print("[完成] 已退出")


if __name__ == "__main__":
    main()
