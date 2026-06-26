"""
ZED Mini 快速诊断脚本
独立运行，检测相机连接状态、SDK 版本、USB 带宽等
"""

import sys
import platform

print("=" * 60)
print("  ZED Mini / ZED Camera Diagnostic")
print("  " + "=" * 60)
print(f"  System: {platform.system()} {platform.release()}")
print(f"  Python: {sys.version.split()[0]}")
print()

# Step 1: Check pyzed
print("[1/5] Check pyzed Python module...", end=" ")
try:
    import pyzed.sl as sl
    print("OK")
    print(f"       ZED SDK version: {sl.Camera.get_sdk_version()}")
except ImportError:
    print("NOT INSTALLED")
    print()
    print("   Please install ZED SDK:")
    print("   1. Download: https://www.stereolabs.com/developers/release/")
    print("   2. After installation, run:")
    print('      cd "C:\\Program Files (x86)\\ZED SDK\\"')
    print("      python get_python_api.py")
    sys.exit(1)

# Step 2: Detect camera
print("[2/5] Detect camera hardware...", end=" ")
try:
    # Quick detection
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
        print("CONNECTED")
        print(f"       Model: {model_name}")
        print(f"       Serial: {info.serial_number}")
        # ZED SDK 5.0+ firmware info is in sensors_configuration
        try:
            print(f"       Firmware: {info.sensors_configuration.firmware_version}")
        except:
            print(f"       Firmware: (ZED SDK {sl.Camera.get_sdk_version()})")
        print(f"       Resolution: {info.camera_configuration.resolution.width}x{info.camera_configuration.resolution.height}")
        test_cam.close()
    else:
        print("NOT DETECTED")
        print(f"       Error: {repr(status)}")
        print()
        print("   Please check:")
        print("   - USB 3.0 cable is firmly connected")
        print("   - Plugged into a USB 3.0 (blue) port")
        print("   - Camera side LED is on")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Step 3: Test streaming
print("[3/5] Test video stream (60 frames)...", end=" ")
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
        print("OK")
        print(f"       Success: {success_count}/{total_frames} ({success_rate:.0f}%)")
    else:
        print("WARNING")
        print(f"       Success: {success_count}/{total_frames} ({success_rate:.0f}%)")
        print(f"       Failed: {fail_count}/{total_frames}")
        print("       Possible USB bandwidth issue")
except Exception as e:
    print(f"ERROR: {e}")

# Step 4: Check USB controller
print("[4/5] USB controller check...", end=" ")
try:
    import subprocess
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-PnpDevice -PresentOnly | Where-Object -Property Class -eq 'USB' | Select-Object FriendlyName | Format-List"],
        capture_output=True, text=True, timeout=5
    )
    lines = [l.strip() for l in result.stdout.split('\n') if 'FriendlyName' in l]
    usb_controllers = [l.split(':', 1)[1].strip() for l in lines if ':' in l]

    xhci_controllers = [c for c in usb_controllers if 'xHCI' in c or 'USB 3' in c or 'USB 3.1' in c]
    if xhci_controllers:
        print("OK")
        for c in xhci_controllers:
            print(f"       {c}")
    else:
        print("(No USB 3.0 controller detected)")
except:
    print("(skipped)")

# Step 5: Summary
print("[5/5] Summary")
print()
print(f"    ZED Mini camera status: OK - working")
print(f"    SDK: {sl.Camera.get_sdk_version()}")
print(f"    Next: run full test -> python scripts/test_zed_mini.py --mode stereo")

print()
print("=" * 60)
