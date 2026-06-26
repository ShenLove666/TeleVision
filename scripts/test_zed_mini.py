"""
ZED Mini Basic Test Script
Tests camera connection, video capture, left/right image capture

Usage:
    python scripts/test_zed_mini.py                    # default mode
    python scripts/test_zed_mini.py --mode webcam      # single-cam preview
    python scripts/test_zed_mini.py --mode stereo      # stereo side-by-side preview
    python scripts/test_zed_mini.py --save             # save test images to outputs/
"""

import argparse
import os
import sys
import time
import numpy as np

try:
    import cv2
except ImportError:
    print("Error: need opencv-python: pip install opencv-python")
    sys.exit(1)

try:
    import pyzed.sl as sl
except ImportError:
    print("Error: pyzed module not installed.")
    print("   First install ZED SDK: https://www.stereolabs.com/developers/release/")
    print("   Then run: cd \"C:\\Program Files (x86)\\ZED SDK\\\" && python get_python_api.py")
    sys.exit(1)


def check_camera_connected():
    """Quick check if camera is connected"""
    print("\nChecking ZED Mini camera...")
    try:
        print(f"   ZED SDK version: {sl.Camera.get_sdk_version()}")
        return True
    except Exception as e:
        print(f"   SDK error: {e}")
        return False


def test_basic_stream(args):
    """
    Basic test: open camera, capture stereo images, display/save
    """
    print("\n" + "=" * 60)
    print("  ZED Mini Basic Test")
    print("=" * 60)

    # --- Init parameters ---
    init_params = sl.InitParameters()
    init_params.camera_resolution = args.resolution_enum
    init_params.camera_fps = args.fps
    init_params.depth_mode = sl.DEPTH_MODE.NONE
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    init_params.sdk_verbose = 0

    res_label = f"{args.resolution}"
    print(f"\nOpening camera...")
    print(f"   Resolution: {res_label}")
    print(f"   FPS: {init_params.camera_fps}")

    zed = sl.Camera()
    status = zed.open(init_params)

    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Camera open failed: {repr(status)}")
        print(f"   Error code: {status}")
        return False

    # Get camera info
    cam_info = zed.get_camera_information()
    model_map = {
        sl.MODEL.ZED: "ZED",
        sl.MODEL.ZED_M: "ZED Mini",
        sl.MODEL.ZED2: "ZED 2",
        sl.MODEL.ZED2i: "ZED 2i",
        sl.MODEL.ZED_X: "ZED X",
        sl.MODEL.ZED_XM: "ZED X Mini",
    }
    model_name = model_map.get(cam_info.camera_model, str(cam_info.camera_model))
    print(f"Camera model: {model_name}")
    print(f"Serial: {cam_info.serial_number}")
    print(f"SDK version: {sl.Camera.get_sdk_version()}")

    # --- Runtime parameters ---
    runtime_params = sl.RuntimeParameters()
    # Default sensing mode is standard (STANDARD removed in SDK 5.0)

    # --- Image containers ---
    image_left = sl.Mat()
    image_right = sl.Mat()

    # Output directory
    if args.save:
        os.makedirs("outputs", exist_ok=True)

    # --- Main loop ---
    print("\nCapturing... (press 'q' to quit, 's' to save frame)\n")

    frame_count = 0
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = 0

    try:
        while True:
            loop_start = time.time()

            # Grab a frame
            err = zed.grab(runtime_params)

            if err == sl.ERROR_CODE.SUCCESS:
                # Get left and right images
                zed.retrieve_image(image_left, sl.VIEW.LEFT)
                zed.retrieve_image(image_right, sl.VIEW.RIGHT)

                # Convert to numpy array (BGRA -> BGR)
                left_bgr = image_left.numpy()
                right_bgr = image_right.numpy()

                if left_bgr.shape[2] == 4:
                    left_bgr = cv2.cvtColor(left_bgr, cv2.COLOR_BGRA2BGR)
                if right_bgr.shape[2] == 4:
                    right_bgr = cv2.cvtColor(right_bgr, cv2.COLOR_BGRA2BGR)

                # FPS stats
                fps_counter += 1
                if fps_counter >= 30:
                    current_fps = fps_counter / (time.time() - fps_start_time)
                    fps_counter = 0
                    fps_start_time = time.time()

                # Overlay info on image
                h, w = left_bgr.shape[:2]
                info_text = f"FPS: {current_fps:.1f} | Size: {w}x{h} | Frame: {frame_count}"
                cv2.putText(left_bgr, info_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(right_bgr, info_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Display based on mode
                if args.mode == "stereo":
                    # Stereo side-by-side
                    stereo_view = np.hstack((left_bgr, right_bgr))
                    # Divider line
                    mid_x = stereo_view.shape[1] // 2
                    cv2.line(stereo_view, (mid_x, 0), (mid_x, stereo_view.shape[0]),
                             (0, 255, 0), 2)
                    cv2.putText(stereo_view, "LEFT", (w // 2 - 60, h - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    cv2.putText(stereo_view, "RIGHT", (w + w // 2 - 60, h - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    display_img = stereo_view
                else:
                    # Left eye only
                    display_img = left_bgr

                cv2.imshow("ZED Mini Test (q: quit, s: save)", display_img)

            elif err == sl.ERROR_CODE.END_OF_SYMBOL:
                print("Capture ended")
                break
            else:
                print(f"Grab error: {repr(err)}")

            # Key handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nUser quit")
                break
            elif key == ord('s') and args.save:
                timestamp = int(time.time())
                cv2.imwrite(f"outputs/zed_left_{timestamp}.png", left_bgr)
                cv2.imwrite(f"outputs/zed_right_{timestamp}.png", right_bgr)
                print(f"Saved: outputs/zed_left_{timestamp}.png")

            frame_count += 1

    except KeyboardInterrupt:
        print("\nUser interrupted")

    finally:
        zed.close()
        cv2.destroyAllWindows()
        print(f"\nStats: {frame_count} frames captured")
        print("Test complete")

    return True


def main():
    parser = argparse.ArgumentParser(description="ZED Mini Camera Test Tool")
    parser.add_argument("--mode", type=str, default="stereo",
                        choices=["webcam", "stereo"],
                        help="Display mode: webcam=mono, stereo=side-by-side (default: stereo)")
    parser.add_argument("--save", action="store_true",
                        help="Save test images to outputs/ directory")
    parser.add_argument("--fps", type=int, default=60,
                        help="Camera FPS (default: 60)")
    parser.add_argument("--resolution", type=str, default="HD720",
                        choices=["HD720", "HD1080", "HD1200", "VGA"],
                        help="Camera resolution (default: HD720)")
    args = parser.parse_args()

    # Resolution mapping
    res_map = {
        "HD720": sl.RESOLUTION.HD720,
        "HD1080": sl.RESOLUTION.HD1080,
        "HD1200": sl.RESOLUTION.HD1200,
        "VGA": sl.RESOLUTION.VGA,
    }
    args.resolution_enum = res_map[args.resolution]

    print("+------------------------------------+")
    print("|     ZED Mini Camera Test Tool      |")
    print("+------------------------------------+")
    print(f"  Resolution: {args.resolution}")
    print(f"  FPS:        {args.fps}")
    print(f"  Mode:       {args.mode}")
    print(f"  Save:       {args.save}")
    print("+------------------------------------+")

    test_basic_stream(args)


if __name__ == "__main__":
    main()
