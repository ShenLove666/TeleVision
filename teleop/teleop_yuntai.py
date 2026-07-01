"""
云台 (YunTai / Pan-Tilt) + ZED Mini + Quest VR 头部追踪
====================================================
整合三个功能：
  1. ZED Mini 双目画面 → Quest VR 头显 (实时串流)
  2. Quest 头部追踪 → 云台舵机跟随 (yaw → 下舵机, pitch → 上舵机)
  3. 串口控制云台 (与 yuntai/python_demo.py 协议兼容)

使用方法:
  python teleop/teleop_yuntai.py

依赖:
  - ZED SDK + Python API
  - pyserial
  - vuer
  - pytransform3d

串口协议: (来自 WHEELTEC 云台)
  Byte 0: 0xFF (帧头)
  Byte 1: 0xFE (帧头)
  Byte 2: angle_bottom (下舵机/偏航, 0-270°)
  Byte 3: angle_top    (上舵机/俯仰, 0-180°)
  Bytes 4-7: 0x00 (填充)
  Byte 8: XOR 校验
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import time
import cv2
import serial
from constants_vuer import grd_yup2grd_zup
from TeleVision import OpenTeleVision
import pyzed.sl as sl
from multiprocessing import shared_memory, Queue, Event
from pytransform3d import rotations

# ============================================================
# 可调参数
# ============================================================

# --- 串口 ---
SERIAL_PORT = '/dev/ttyACM0'     # 根据实际情况修改
SERIAL_BAUD = 115200

# --- ZED ---
ZED_RESOLUTION = sl.RESOLUTION.HD720
ZED_FPS = 60
CROP_W = 0      # 水平裁剪（每侧像素）
CROP_H = 0      # 垂直裁剪（顶部像素）

# --- 舵机角度映射 ---
# 下舵机 (pan/base) - 范围 0~270°
SERVO_BOTTOM_MIN = 0
SERVO_BOTTOM_MAX = 270
SERVO_BOTTOM_CENTER = 135   # 正前方时角度

# 上舵机 (tilt/arm) - 范围 0~180°
SERVO_TOP_MIN = 0
SERVO_TOP_MAX = 180
SERVO_TOP_CENTER = 90       # 水平时角度

# 头部角度范围 (超出会被限幅)
# yaw: 左右转头, 负=左, 正=右
YAW_RANGE_DEG = 90          # ±90° → 对应下舵机全行程
# pitch: 上下抬头, 负=向下看, 正=向上看
PITCH_RANGE_DEG = 60        # ±60° → 对应上舵机全行程

# --- 平滑滤波 ---
SMOOTHING = 0.3             # 0=无平滑, 1=完全跟随 (指数移动平均)
DEAD_ZONE_DEG = 0.5         # 死区 (度), 防止微小抖动

# --- 打印 ---
PRINT_FPS = True
PRINT_ANGLES = False

# ============================================================
# 串口控制函数
# ============================================================

class YunTaiController:
    """云台串口控制器"""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self._last_bottom = -1  # 用于去重
        self._last_top = -1

    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            print(f"[YunTai] 串口已打开: {self.port} @ {self.baud}")
            return True
        except serial.SerialException as e:
            print(f"[YunTai] 串口打开失败: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[YunTai] 串口已关闭")

    def send_angles(self, angle_bottom: int, angle_top: int):
        """
        发送舵机角度
        angle_bottom: 下舵机 (pan), 0~270
        angle_top:    上舵机 (tilt), 0~180
        """
        # 限幅
        angle_bottom = max(SERVO_BOTTOM_MIN, min(SERVO_BOTTOM_MAX, int(round(angle_bottom))))
        angle_top = max(SERVO_TOP_MIN, min(SERVO_TOP_MAX, int(round(angle_top))))

        # 去重: 角度没变就不发
        if angle_bottom == self._last_bottom and angle_top == self._last_top:
            return
        self._last_bottom = angle_bottom
        self._last_top = angle_top

        # 计算 XOR 校验
        parity = angle_bottom ^ angle_top

        # 组包
        packet = [0xFF, 0xFE, angle_bottom, angle_top, 0x00, 0x00, 0x00, 0x00, 0x00, parity]
        try:
            self.ser.write(bytes(packet))
        except serial.SerialException as e:
            print(f"[YunTai] 发送失败: {e}")

    def is_open(self):
        return self.ser is not None and self.ser.is_open


# ============================================================
# 角度映射函数
# ============================================================

def head_yaw_to_servo(yaw_deg: float) -> int:
    """
    将头部 yaw 角度映射到下舵机角度 (pan)
    yaw_deg: 负=左, 正=右 (来自头追踪)
    返回: 0~270 舵机角度
    """
    # 归一化到 [-1, 1]
    norm = np.clip(yaw_deg / YAW_RANGE_DEG, -1.0, 1.0)
    # 映射到舵机范围: 左→小角度, 右→大角度
    if norm < 0:
        return int(SERVO_BOTTOM_CENTER + norm * (SERVO_BOTTOM_CENTER - SERVO_BOTTOM_MIN))
    else:
        return int(SERVO_BOTTOM_CENTER + norm * (SERVO_BOTTOM_MAX - SERVO_BOTTOM_CENTER))


def head_pitch_to_servo(pitch_deg: float) -> int:
    """
    将头部 pitch 角度映射到上舵机角度 (tilt)
    pitch_deg: 负=向下, 正=向上
    返回: 0~180 舵机角度
    """
    norm = np.clip(pitch_deg / PITCH_RANGE_DEG, -1.0, 1.0)
    # 向下看→小角度, 向上看→大角度 (取决于安装方式, 可反转符号)
    if norm < 0:
        return int(SERVO_TOP_CENTER + norm * (SERVO_TOP_CENTER - SERVO_TOP_MIN))
    else:
        return int(SERVO_TOP_CENTER + norm * (SERVO_TOP_MAX - SERVO_TOP_CENTER))


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("  云台 (YunTai) + ZED Mini + Quest VR 头部追踪")
    print("=" * 60)

    # ---- 1. 初始化云台串口 ----
    yuntai = YunTaiController(SERIAL_PORT, SERIAL_BAUD)
    if not yuntai.open():
        print("!! 云台串口打开失败, 请检查端口号")
        print("   尝试: ls /dev/ttyACM* /dev/ttyUSB* /dev/ttyTHS*")
        return
    # 初始回中
    yuntai.send_angles(SERVO_BOTTOM_CENTER, SERVO_TOP_CENTER)

    # ---- 2. 初始化 ZED Mini ----
    print("\n[ZED] 初始化相机...")
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = ZED_RESOLUTION
    init_params.camera_fps = ZED_FPS

    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"[ZED] 打开失败: {repr(err)}")
        yuntai.close()
        return
    print(f"[ZED] 相机已打开, 分辨率: {ZED_RESOLUTION}, {ZED_FPS}fps")

    resolution = (720, 1280)
    resolution_cropped = (resolution[0] - CROP_H, resolution[1] - 2 * CROP_W)

    # ---- 3. 初始化共享内存与 OpenTeleVision ----
    print("[VR] 启动 OpenTeleVision 服务器...")
    img_shape = (resolution_cropped[0], 2 * resolution_cropped[1], 3)
    shm = shared_memory.SharedMemory(create=True, size=np.prod(img_shape) * np.uint8().itemsize)
    img_array = np.ndarray((img_shape[0], img_shape[1], 3), dtype=np.uint8, buffer=shm.buf)
    image_queue = Queue()
    toggle_streaming = Event()

    # 如果没证书就允许不加密 (ngrok=True)
    cert_path = os.path.join(os.path.dirname(__file__), "cert.pem")
    use_ngrok = not os.path.exists(cert_path)
    if use_ngrok:
        print("[VR] 未找到 cert.pem, 使用 ngrok 模式 (无证书)")
    else:
        print("[VR] 找到 cert.pem, 使用本地证书模式")

    tv = OpenTeleVision(
        resolution_cropped,
        shm.name,
        image_queue,
        toggle_streaming,
        stream_mode="image",
        ngrok=use_ngrok,
    )

    # 等待服务器启动
    time.sleep(2)

    print("\n" + "=" * 60)
    print("  服务器已启动!")
    print("  1. 在 Quest 浏览器中打开对应地址")
    print("  2. 点击 'Enter VR' 进入")
    print("  3. 头部转动 → 云台跟随")
    print("=" * 60 + "\n")

    # ---- 4. 图像缓存与主循环 ----
    image_left = sl.Mat()
    image_right = sl.Mat()
    runtime_parameters = sl.RuntimeParameters()

    # 平滑滤波状态
    smooth_yaw_deg = 0.0
    smooth_pitch_deg = 0.0

    frame_count = 0
    fps_timer = time.time()

    print("[主循环] 开始运行... (Ctrl+C 退出)\n")

    try:
        while True:
            loop_start = time.time()

            # ----- A. 获取头部姿态 (来自 Quest) -----
            head_mat = grd_yup2grd_zup[:3, :3] @ tv.head_matrix[:3, :3] @ grd_yup2grd_zup[:3, :3].T
            if np.sum(head_mat) == 0:
                head_mat = np.eye(3)

            try:
                head_rot = rotations.quaternion_from_matrix(head_mat[0:3, 0:3])
                # 顺序: yaw (Z), pitch (Y), roll (X)
                ypr = rotations.euler_from_quaternion(head_rot, 2, 1, 0, False)
                raw_yaw_deg = np.degrees(ypr[0])   # Z轴: 左右转头
                raw_pitch_deg = np.degrees(ypr[1])  # Y轴: 上下点头

                # 死区
                if abs(raw_yaw_deg) < DEAD_ZONE_DEG:
                    raw_yaw_deg = 0
                if abs(raw_pitch_deg) < DEAD_ZONE_DEG:
                    raw_pitch_deg = 0

                # 指数平滑 (低通滤波)
                smooth_yaw_deg = smooth_yaw_deg * (1 - SMOOTHING) + raw_yaw_deg * SMOOTHING
                smooth_pitch_deg = smooth_pitch_deg * (1 - SMOOTHING) + raw_pitch_deg * SMOOTHING

                # 映射到舵机角度
                servo_bottom = head_yaw_to_servo(smooth_yaw_deg)
                servo_top = head_pitch_to_servo(smooth_pitch_deg)

                # 发送到云台
                yuntai.send_angles(servo_bottom, servo_top)

                if PRINT_ANGLES:
                    print(f"  Yaw={raw_yaw_deg:+.1f}°→{smooth_yaw_deg:+.1f}°  "
                          f"Pitch={raw_pitch_deg:+.1f}°→{smooth_pitch_deg:+.1f}°  "
                          f"Servo=({servo_bottom}, {servo_top})")

            except Exception as e:
                # 头部数据可能暂时无效
                pass

            # ----- B. 获取 ZED 图像并发送到 Quest -----
            if zed.grab(runtime_parameters) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_left, sl.VIEW.LEFT)
                zed.retrieve_image(image_right, sl.VIEW.RIGHT)

                left_img = image_left.numpy()
                right_img = image_right.numpy()

                # 裁剪
                if CROP_W > 0:
                    left_img = left_img[CROP_H:, CROP_W:-CROP_W]
                    right_img = right_img[CROP_H:, CROP_W:-CROP_W]
                else:
                    left_img = left_img[CROP_H:]
                    right_img = right_img[CROP_H:]

                bgr = np.hstack((left_img, right_img))
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGRA2RGB)

                np.copyto(img_array, rgb)
                image_queue.put(rgb)

            # ----- C. 速率统计 & 帧率控制 -----
            frame_count += 1
            if PRINT_FPS and frame_count % 30 == 0:
                elapsed = time.time() - fps_timer
                fps_total = frame_count / elapsed
                print(f"\r  总 FPS: {fps_total:.1f}", end="")
                # 重置计数器
                frame_count = 0
                fps_timer = time.time()

            # 控制循环速率 ~60Hz (但不精确 sleep, 因为 serial write 可能阻塞)
            elapsed = time.time() - loop_start
            sleep_time = max(0, 1.0 / 60 - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n[退出] 用户中断")
    except Exception as e:
        print(f"\n[错误] {e}")
    finally:
        # ---- 清理 ----
        print("[清理] 复位舵机到中心位置...")
        yuntai.send_angles(SERVO_BOTTOM_CENTER, SERVO_TOP_CENTER)
        time.sleep(0.5)
        yuntai.close()

        print("[清理] 关闭 ZED...")
        zed.close()

        print("[清理] 释放共享内存...")
        shm.unlink()

        print("[完成] 程序已退出")


if __name__ == "__main__":
    main()
