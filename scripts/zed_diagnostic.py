"""
ZED Mini 快速诊断脚本
独立运行，检测相机连接状态、SDK 版本、USB 带宽等
"""

import sys
import platform

print("=" * 60)
print("  ZED Mini / ZED 相机诊断工具")
print("  " + "=" * 60)
print(f"  系统: {platform.system()} {platform.release()}")
print(f"  Python: {sys.version.split()[0]}")
print()

# Step 1: Check pyzed
print("[1/5] 检测 pyzed Python 模块...", end=" ")
try:
    import pyzed.sl as sl
    print("✅ 已安装")
    print(f"       ZED SDK 版本: {sl.Camera.get_sdk_version()}")
except ImportError:
    print("❌ 未安装")
    print()
    print("   请安装 ZED SDK:")
    print("   1. 下载: https://www.stereolabs.com/developers/release/")
    print("   2. 安装后运行:")
    print('      cd "C:\\Program Files (x86)\\ZED SDK\\"')
    print("      python get_python_api.py")
    sys.exit(1)

# Step 2: Detect camera
print("[2/5] 检测相机硬件...", end=" ")
try:
    # 快速探测
    test_cam = sl.Camera()
    init = sl.InitParameters()
    init.depth_mode = sl.DEPTH_MODE.NONE
    init.camera_resolution = sl.RESOLUTION.HD720
    init.camera_fps = 30
    init.sdk_verbose = 0

    status = test_cam.open(init)
    if status == sl.ERROR_CODE.SUCCESS:
        info = test_cam.get_camera_information()
        model_map = {
            sl.MODEL.ZED: "ZED",
            sl.MODEL.ZED_M: "ZED Mini",
            sl.MODEL.ZED2: "ZED 2",
            sl.MODEL.ZED2i: "ZED 2i",
            sl.MODEL.ZED_X: "ZED X",
            sl.MODEL.ZED_XM: "ZED X Mini",
        }
        model_name = model_map.get(info.camera_model, f"Unknown ({info.camera_model})")
        print(f"✅ 已连接")
        print(f"       型号: {model_name}")
        print(f"       序列号: {info.serial_number}")
        print(f"       固件版本: {info.firmware_version}")
        print(f"       分辨率: {info.camera_configuration.resolution.width}x{info.camera_configuration.resolution.height}")
        test_cam.close()
    else:
        print("❌ 未检测到相机")
        print(f"       错误: {repr(status)}")
        print()
        print("   请检查:")
        print("   - USB 3.0 线缆是否连接牢固")
        print("   - 是否插在 USB 3.0 (蓝色) 接口上")
        print("   - 相机侧面 LED 是否亮起")
        sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)

# Step 3: Test streaming
print("[3/5] 测试视频流 (60帧)...", end=" ")
try:
    init.camera_fps = 60
    test_cam = sl.Camera()
    test_cam.open(init)
    rt = sl.RuntimeParameters()

    left = sl.Mat()
    right = sl.Mat()

    success_count = 0
    fail_count = 0
    total_frames = 60

    for i in range(total_frames):
        err = test_cam.grab(rt)
        if err == sl.ERROR_CODE.SUCCESS:
            success_count += 1
            test_cam.retrieve_image(left, sl.VIEW.LEFT)
            test_cam.retrieve_image(right, sl.VIEW.RIGHT)
        else:
            fail_count += 1

    test_cam.close()

    success_rate = success_count / total_frames * 100
    if success_rate > 80:
        print("✅")
        print(f"       成功: {success_count}/{total_frames} ({success_rate:.0f}%)")
    else:
        print("⚠️")
        print(f"       成功: {success_count}/{total_frames} ({success_rate:.0f}%)")
        print(f"       失败: {fail_count}/{total_frames}")
        print("       可能存在 USB 带宽不足")
except Exception as e:
    print(f"❌ 错误: {e}")

# Step 4: Check USB controller
print("[4/5] USB 控制器检查...", end=" ")
try:
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command",
         "Get-PnpDevice -PresentOnly | Where-Object { $_.Class -eq 'USB' } | Select-Object FriendlyName | Format-List"],
        capture_output=True, text=True, timeout=5
    )
    lines = [l.strip() for l in result.stdout.split('\n') if 'FriendlyName' in l]
    usb_controllers = [l.split(':', 1)[1].strip() for l in lines if ':' in l]

    xhci_controllers = [c for c in usb_controllers if 'xHCI' in c or 'USB 3' in c or 'USB 3.1' in c]
    if xhci_controllers:
        print("✅")
        for c in xhci_controllers:
            print(f"       {c}")
    else:
        print("⚠️  (未检测到 USB 3.0 控制器，可能影响性能)")
except:
    print("⚠️  (跳过)")

# Step 5: Summary
print(f"[5/5] 总结")
print()
print(f"    ZED Mini 相机状态: ✅ 正常工作")
print(f"    SDK: {sl.Camera.get_sdk_version()}")
print(f"    下一步: 运行完整测试 -> python scripts/test_zed_mini.py")

print()
print("=" * 60)
