import argparse
import cv2
import numpy as np
from ultralytics import YOLO
import sys
import os
import json
import base64
from PIL import Image, ImageDraw, ImageFont

# Try to import MediaPipe Tasks API
MP_TASKS_AVAILABLE = False
mp = None
# try:
#     import mediapipe as mp
#     from mediapipe.tasks import python
#     from mediapipe.tasks.python import vision
#     MP_TASKS_AVAILABLE = True
# except ImportError:
#     MP_TASKS_AVAILABLE = False
#     mp = None

# Hand connections for drawing (Standard MediaPipe Hand Connections)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # Index
    (5, 9), (9, 10), (10, 11), (11, 12),      # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # Ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky & Palm
]

def draw_chinese_text(img, text, position, font, color=(0, 0, 255), bold=0):
    """
    Draws Chinese text on an image using PIL.
    """
    # Convert OpenCV image (BGR) to PIL image (RGB)
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    
    # Draw text
    if bold and bold > 0:
        x, y = position
        for dx in range(-bold, bold + 1):
            for dy in range(-bold, bold + 1):
                draw.text((x + dx, y + dy), text, font=font, fill=color)
    else:
        draw.text(position, text, font=font, fill=color)
    
    # Convert back to OpenCV image (BGR)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def draw_landmarks_on_image(rgb_image, detection_result, offset=(0, 0)):
    """
    Draws hand landmarks on the image.
    Args:
      rgb_image: A numpy array representing the RGB image.
      detection_result: The detection result from HandLandmarker.
      offset: (x, y) offset to add to landmark coordinates (e.g., ROI offset).
    """
    hand_landmarks_list = detection_result.hand_landmarks
    annotated_image = np.copy(rgb_image)
    rx, ry = offset

    # Loop through the detected hands to visualize.
    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]

        # Convert normalized landmarks to pixel coordinates
        height, width, _ = annotated_image.shape
        pixel_landmarks = []
        for landmark in hand_landmarks:
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            pixel_landmarks.append((x + rx, y + ry))

        # Draw connections
        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            cv2.line(annotated_image, pixel_landmarks[start_idx], pixel_landmarks[end_idx], 
                     (0, 255, 0), 2) # Green color for connections

        # Draw landmarks
        for landmark_px in pixel_landmarks:
             cv2.circle(annotated_image, landmark_px, 2, (0, 0, 255), -1) # Red color for landmarks

    return annotated_image

def select_roi_and_threshold(video_path):
    """
    Opens the first frame of the video, allows user to select ROI,
    and input a threshold via terminal.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        sys.exit(1)
        
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Could not read first frame for ROI selection.")
        sys.exit(1)

    print("\n--- Step 1: Select ROI ---")
    print("Draw a rectangle on the window and press ENTER/SPACE to confirm.")
    print("Press 'c' to cancel selection (use full screen).")
    
    # Select ROI
    # cv2.selectROI returns (x, y, w, h)
    # winName, img, showCrosshair, fromCenter
    roi = cv2.selectROI("Select ROI (Press Enter to Confirm)", frame, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow("Select ROI (Press Enter to Confirm)")
    
    # If width or height is 0, user cancelled or selected nothing -> use full screen
    x, y, w, h = roi
    if w == 0 or h == 0:
        print("No ROI selected, using full frame.")
        roi = (0, 0, frame.shape[1], frame.shape[0])
    else:
        print(f"ROI Selected: x={x}, y={y}, w={w}, h={h}")

    print("\n--- Step 2: Input Threshold ---")
    while True:
        try:
            val = input("Enter minimum detection threshold (0.0 - 1.0) [default 0.5]: ").strip()
            if not val:
                threshold = 0.5
                break
            threshold = float(val)
            if 0.0 <= threshold <= 1.0:
                break
            print("Please enter a value between 0.0 and 1.0.")
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    return roi, threshold

def load_actions(json_path):
    """
    Load actions from the result JSON file.
    Returns a list of actions or empty list if failed.
    """
    if not json_path:
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both possible structures: direct list or nested in model_output
            if "model_output" in data and "actions" in data["model_output"]:
                return data["model_output"]["actions"]
            elif "actions" in data:
                return data["actions"]
            else:
                print("Warning: Could not find 'actions' list in JSON.")
                return []
    except Exception as e:
        print(f"Warning: Failed to load JSON: {e}")
        return []

def get_current_action(timestamp, actions):
    """
    Find the action active at the current timestamp.
    """
    for action in actions:
        start = action.get("start_time", 0)
        end = action.get("end_time", 0)
        if start <= timestamp <= end:
            return action.get("label", "")
    return ""

def process_video(input_path, output_path, json_path=None, show_preview=False, no_gui=False, threshold=0.5):
    # 0. User Configuration Step
    if no_gui:
        cap_tmp = cv2.VideoCapture(input_path)
        if not cap_tmp.isOpened():
            print(f"Error opening video: {input_path}")
            return
        w = int(cap_tmp.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap_tmp.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap_tmp.release()
        roi = (0, 0, w, h)
        conf_threshold = threshold
    else:
        roi, conf_threshold = select_roi_and_threshold(input_path)
    rx, ry, rw, rh = roi

    # Load actions if JSON provided
    actions_list = load_actions(json_path)
    actions_ready = bool(actions_list)
    last_actions_mtime = None
    if json_path and os.path.exists(json_path):
        try:
            last_actions_mtime = os.path.getmtime(json_path)
        except Exception:
            last_actions_mtime = None
    if actions_list:
        print(f"Loaded {len(actions_list)} actions from {json_path}")
        print("[ACTIONS_READY]")
    else:
        print("No actions loaded.")

    # Initialize font for Chinese text (2x size)
    font_size = 40
    try:
        font = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/STHeiti Light.ttc", font_size)
        except:
            font = ImageFont.load_default()
            print("Warning: Could not load Chinese font, falling back to default.")

    # Load YOLOv8 Pose model
    yolo_model = YOLO("yolov8n-pose.pt")

    # Initialize MediaPipe Hands (Tasks API)
    landmarker = None
    
    if MP_TASKS_AVAILABLE:
        try:
            base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=conf_threshold,
                min_hand_presence_confidence=conf_threshold,
                min_tracking_confidence=conf_threshold
            )
            landmarker = vision.HandLandmarker.create_from_options(options)
            print("MediaPipe HandLandmarker initialized successfully.")
        except Exception as e:
            print(f"Warning: Failed to initialize MediaPipe HandLandmarker: {e}")
            print("Hand tracking will be skipped.")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Error opening video file: {input_path}")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Define video writer
    # Use 'mp4v' for stable writing in OpenCV, then convert with ffmpeg for web
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Processing {input_path} -> {output_path}...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Progress indicator
        frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_idx < 5 or frame_idx % 30 == 0:
            print(f"Processing frame {frame_idx}/{total_frames}...", end='\r')
            
        if json_path and (frame_idx % 60 == 0):
            try:
                if os.path.exists(json_path):
                    m = os.path.getmtime(json_path)
                    if (last_actions_mtime is None) or (m > last_actions_mtime):
                        actions_list = load_actions(json_path)
                        last_actions_mtime = m
                        if (not actions_ready) and actions_list:
                            actions_ready = True
                            print("[ACTIONS_READY]")
            except Exception:
                pass
            
        frame_idx_for_time = frame_idx - 1 if frame_idx > 0 else 0
        if fps and fps > 0:
            current_time_sec = frame_idx_for_time / fps
        else:
            current_time_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        # Crop frame to ROI for processing? 
        # Or just filter detections outside ROI?
        # Usually it's better to process the ROI to speed up detection, 
        # but here we need to map coordinates back to original frame.
        # For simplicity, let's process the cropped area.
        
        roi_frame = frame[ry:ry+rh, rx:rx+rw]
        if roi_frame.size == 0:
            out.write(frame)
            continue

        # 1. YOLOv8 Pose Inference on ROI
        # conf=conf_threshold filters YOLO detections by confidence
        yolo_results = yolo_model(roi_frame, verbose=False, conf=conf_threshold)
        
        # We use a copy of the original frame to avoid drawing YOLO's default skeletons/boxes
        # Note: We need to draw on the full frame
        annotated_frame = frame.copy()

        current_label = get_current_action(current_time_sec, actions_list)
        boxes = []
        # Extract keypoints to find wrists for the green rectangle
        # YOLOv8-Pose keypoint indices: 9=left_wrist, 10=right_wrist
        if yolo_results[0].keypoints is not None:
            keypoints = yolo_results[0].keypoints.xy.cpu().numpy()  # shape: (num_persons, 17, 2)
            
            for person_kpts in keypoints:
                # Check if we have valid coordinates for wrists
                left_wrist = person_kpts[9]
                right_wrist = person_kpts[10]

                # Coordinates are relative to ROI, need to shift back to full frame
                # if not (0,0)
                if np.any(left_wrist):
                    left_wrist[0] += rx
                    left_wrist[1] += ry
                if np.any(right_wrist):
                    right_wrist[0] += rx
                    right_wrist[1] += ry

                if np.any(left_wrist) and np.any(right_wrist):
                    # Basic filtering: if any point is still (0,0) or low confidence (handled by model conf)
                    # We assume (0,0) is invalid
                    if left_wrist[0] == rx and left_wrist[1] == ry: continue
                    if right_wrist[0] == rx and right_wrist[1] == ry: continue

                    pt1 = (int(left_wrist[0]), int(left_wrist[1]))
                    pt2 = (int(right_wrist[0]), int(right_wrist[1]))
                    
                    # Expand the rectangle by 30 pixels
                    padding = 30
                    x1 = min(pt1[0], pt2[0]) - padding
                    y1 = min(pt1[1], pt2[1]) - padding
                    x2 = max(pt1[0], pt2[0]) + padding
                    y2 = max(pt1[1], pt2[1]) + padding
                    
                    # Ensure within frame bounds
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(width, x2)
                    y2 = min(height, y2)
                    
                    # Draw green rectangle using wrists as diagonal corners
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    boxes.append((x1, y1, x2, y2))

        # 2. MediaPipe Hands Inference (Tasks API)
        if landmarker:
            # Convert ROI to RGB
            rgb_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_roi)
            
            # Detect
            detection_result = landmarker.detect(mp_image)

            # Draw landmarks
            # Note: We draw on the annotated_frame (which is full size BGR)
            # But detection was on roi_frame.
            # We need to be careful with coordinate spaces.
            # draw_landmarks_on_image helper takes an RGB image and returns an annotated RGB image.
            # But we want to draw on our BGR annotated_frame.
            # We can modify draw_landmarks_on_image to draw on our BGR frame directly or use its logic here.
            
            # Let's just use the logic inline or call a modified helper that draws on BGR.
            # Actually, draw_landmarks_on_image above returns a copy. 
            # Let's just reuse the logic to draw directly on annotated_frame (BGR).
            
            if detection_result.hand_landmarks:
                 # Pass annotated_frame (BGR) but treat it as the canvas. 
                 # The drawing colors in helper are (0,255,0) which is Green in BGR too.
                 # (0,0,255) is Red in BGR.
                 # So it works fine.
                 annotated_frame = draw_landmarks_on_image(annotated_frame, detection_result, offset=(rx, ry))

        if current_label and boxes:
            bbox = font.getbbox(current_label)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            for (x1, y1, x2, y2) in boxes:
                text_x = x2 - text_w - 5
                text_y = y2 - text_h - 5
                text_x = max(x1, text_x)
                text_y = max(y1, text_y)
                annotated_frame = draw_chinese_text(
                    annotated_frame,
                    current_label,
                    (text_x, text_y),
                    font=font,
                    color=(0, 0, 255),
                    bold=2
                )

        # Draw ROI box for visualization (optional, blue box)
        cv2.rectangle(annotated_frame, (rx, ry), (rx+rw, ry+rh), (255, 0, 0), 2)
        
        # 3. Output real-time thumbnail to stdout (base64 encoded)
        # We do this every 5 frames to balance real-time feel and performance
        if frame_idx % 5 == 0:
            try:
                # Resize to smaller thumbnail to reduce data transfer
                thumb_w, thumb_h = 320, int(320 * height / width)
                thumbnail = cv2.resize(annotated_frame, (thumb_w, thumb_h))
                _, buffer = cv2.imencode('.jpg', thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 70])
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                print(f"\n[THUMBNAIL]{jpg_as_text}[THUMBNAIL_END]", flush=True)
            except Exception as e:
                # Silently fail for thumbnail generation
                pass

        # Write frame to output video
        out.write(annotated_frame)

        # Show realtime preview
        if show_preview:
            cv2.imshow("Detection Preview", annotated_frame)
            # Press 'q' to exit early
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Preview stopped by user.")
                break

    cap.release()
    out.release()
    if landmarker:
        landmarker.close()
    if show_preview:
        cv2.destroyAllWindows()
    print("Processing complete.")
    
    # Post-process with ffmpeg for Web compatibility (H.264)
    if os.path.exists(output_path):
        print("Converting to H.264 for Web compatibility using ffmpeg...")
        temp_output = output_path.replace(".mp4", "_temp.mp4")
        os.rename(output_path, temp_output)
        
        # ffmpeg command: -pix_fmt yuv420p is important for broad browser support
        # -loglevel error to reduce noise
        cmd = f"ffmpeg -y -i {temp_output} -vcodec libx264 -pix_fmt yuv420p -loglevel error {output_path}"
        ret = os.system(cmd)
        
        if ret == 0:
            print("Conversion successful.")
            if os.path.exists(temp_output):
                os.remove(temp_output)
        else:
            print("Warning: ffmpeg conversion failed. The video might not play in browser.")
            # Restore original if failed (though it might be broken for web)
            if not os.path.exists(output_path):
                os.rename(temp_output, output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video", help="Path to input video")
    parser.add_argument("--out", default="data-handled.mp4", help="Path to output video")
    parser.add_argument("--show", action="store_true", help="Show realtime preview window")
    parser.add_argument("--json", help="Path to actions JSON file")
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI interactions")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection threshold")
    args = parser.parse_args()
    
    process_video(args.video, args.out, json_path=args.json, show_preview=args.show, no_gui=args.no_gui, threshold=args.threshold)
