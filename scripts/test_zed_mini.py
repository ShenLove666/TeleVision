"""
ZED Mini 基础测试脚本
测试相机连接、视频采集、左右目图像捕获

用法：
    python scripts/test_zed_mini.py                    # 默认模式
    python scripts/test_zed_mini.py --mode webcam      # 伪装成网络摄像头预览
    python scripts/test_zed_mini.py --mode stereo      # 双目预览 + 按帧率统计
    python scripts/test_zed_mini.py --save             # 保存测试图像到 outputs/
"""

import argparse
import os
import sys
import time
import numpy as np

try:
    import cv2
except ImportError:
    print("❌ 需要 opencv-python: pip install opencv-python")
    sys.exit(1)

try:
    import pyzed.sl as sl
except ImportError:
    print("❌ pyzed 模块未安装。")
    print("   请先安装 ZED SDK: https://www.stereolabs.com/developers/release/")
    print("   然后运行: cd \"C:\\Program Files (x86)\\ZED SDK\\\" && python get_python_api.py")
    sys.exit(1)


def check_camera_connected():
    """快速检测相机是否连接"""
    print("\n🔍 检测 ZED Mini 相机...")
    # 创建相机对象但不打开，先检测
    try:
        # 尝试获取已连接的设备列表
        print(f"   ZED SDK 版本: {sl.Camera.get_sdk_version()}")
        return True
    except Exception as e:
        print(f"❌ SDK 错误: {e}")
        return False


def test_basic_stream(args):
    """
    基础测试：打开相机、捕获双目图像、显示/保存
    """
    print("\n" + "=" * 60)
    print("  ZED Mini 基础测试")
    print("=" * 60)

    # --- 初始化参数 ---
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720  # 1280x720
    init_params.camera_fps = 60  # ZED Mini 在 HD720 下支持 60fps
    init_params.depth_mode = sl.DEPTH_MODE.NONE  # 纯视频测试，不需要深度
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    init_params.sdk_verbose = 0  # 减少控制台输出

    print(f"\n📷 打开相机...")
    print(f"   分辨率: HD720 (1280x720)")
    print(f"   帧率: {init_params.camera_fps} fps")

    zed = sl.Camera()
    status = zed.open(init_params)

    if status != sl.ERROR_CODE.SUCCESS:
        print(f"❌ 相机打开失败: {repr(status)}")
        print(f"   错误码: {status}")
        return False

    # 获取相机信息
    cam_info = zed.get_camera_information()
    print(f"✅ 相机型号: {cam_info.camera_model}")
    print(f"✅ 序列号: {cam_info.serial_number}")
    print(f"✅ 固件版本: {cam_info.firmware_version}")
    print(f"✅ SDK 版本: {cam_info.sdk_version}")

    # --- 运行时参数 ---
    runtime_params = sl.RuntimeParameters()
    runtime_params.sensing_mode = sl.SENSING_MODE.STANDARD

    # --- 准备图像容器 ---
    image_left = sl.Mat()
    image_right = sl.Mat()

    # 输出目录
    if args.save:
        os.makedirs("outputs", exist_ok=True)

    # --- 主循环 ---
    print("\n⏳ 开始采集（按 'q' 退出，按 's' 保存当前帧）...\n")

    frame_count = 0
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = 0

    try:
        while True:
            loop_start = time.time()

            # 抓取一帧
            err = zed.grab(runtime_params)

            if err == sl.ERROR_CODE.SUCCESS:
                # 获取左右目图像
                zed.retrieve_image(image_left, sl.VIEW.LEFT)
                zed.retrieve_image(image_right, sl.VIEW.RIGHT)

                # 转换为 numpy 数组 (BGRA -> BGR)
                left_bgr = image_left.numpy()
                right_bgr = image_right.numpy()

                if left_bgr.shape[2] == 4:
                    left_bgr = cv2.cvtColor(left_bgr, cv2.COLOR_BGRA2BGR)
                if right_bgr.shape[2] == 4:
                    right_bgr = cv2.cvtColor(right_bgr, cv2.COLOR_BGRA2BGR)

                # FPS 统计
                fps_counter += 1
                if fps_counter >= 30:
                    current_fps = fps_counter / (time.time() - fps_start_time)
                    fps_counter = 0
                    fps_start_time = time.time()

                # 帧率信息叠加到图像上
                h, w = left_bgr.shape[:2]
                info_text = f"FPS: {current_fps:.1f} | Size: {w}x{h} | Frame: {frame_count}"
                cv2.putText(left_bgr, info_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(right_bgr, info_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 根据模式显示
                if args.mode == "stereo":
                    # 双目并排显示
                    stereo_view = np.hstack((left_bgr, right_bgr))
                    # 添加分割线
                    mid_x = stereo_view.shape[1] // 2
                    cv2.line(stereo_view, (mid_x, 0), (mid_x, stereo_view.shape[0]),
                             (0, 255, 0), 2)
                    cv2.putText(stereo_view, "LEFT", (w // 2 - 60, h - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    cv2.putText(stereo_view, "RIGHT", (w + w // 2 - 60, h - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    display_img = stereo_view
                else:
                    # 仅显示左目
                    display_img = left_bgr

                cv2.imshow("ZED Mini Test (q: quit, s: save)", display_img)

            elif err == sl.ERROR_CODE.END_OF_SYMBOL:
                print("⚠️  采集结束")
                break
            else:
                print(f"⚠️  抓取错误: {repr(err)}")

            # 按键处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n👋 用户退出")
                break
            elif key == ord('s') and args.save:
                timestamp = int(time.time())
                cv2.imwrite(f"outputs/zed_left_{timestamp}.png", left_bgr)
                cv2.imwrite(f"outputs/zed_right_{timestamp}.png", right_bgr)
                print(f"💾 已保存: outputs/zed_left_{timestamp}.png")
                print(f"💾 已保存: outputs/zed_right_{timestamp}.png")

            frame_count += 1

            # 计算并显示单帧处理时间
            elapsed = time.time() - loop_start
            if elapsed > 0.033:  # 超过 30ms 预警
                pass  # 可以在这里添加性能预警

    except KeyboardInterrupt:
        print("\n👋 用户中断")

    finally:
        zed.close()
        cv2.destroyAllWindows()
        print(f"\n📊 统计: 共采集 {frame_count} 帧")
        print("✅ 测试完成")

    return True


def main():
    parser = argparse.ArgumentParser(description="ZED Mini 相机测试工具")
    parser.add_argument("--mode", type=str, default="stereo",
                        choices=["webcam", "stereo"],
                        help="显示模式: webcam=单目, stereo=双目并排 (默认: stereo)")
    parser.add_argument("--save", action="store_true",
                        help="保存测试图像到 outputs/ 目录")
    parser.add_argument("--fps", type=int, default=60,
                        help="相机帧率 (默认: 60)")
    parser.add_argument("--resolution", type=str, default="HD720",
                        choices=["HD720", "HD1080", "HD1200", "VGA"],
                        help="相机分辨率 (默认: HD720)")
    args = parser.parse_args()

    # 分辨率映射
    res_map = {
        "HD720": sl.RESOLUTION.HD720,
        "HD1080": sl.RESOLUTION.HD1080,
        "HD1200": sl.RESOLUTION.HD1200,
        "VGA": sl.RESOLUTION.VGA,
    }
    args.resolution_enum = res_map[args.resolution]

    print(f"""
╔══════════════════════════════════════╗
║      ZED Mini 相机测试工具            ║
╠══════════════════════════════════════╣
║  分辨率: {args.resolution:<18} ║
║  帧率:   {args.fps:<3} fps              ║
║  模式:   {args.mode:<18} ║
║  保存:   {str(args.save):<18} ║
╚══════════════════════════════════════╝
    """)

    test_basic_stream(args)


if __name__ == "__main__":
    main()
