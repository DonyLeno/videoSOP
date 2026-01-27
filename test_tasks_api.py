
import sys
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    HandLandmarker = vision.HandLandmarker
    print("MediaPipe Tasks API HandLandmarker found!")
except ImportError as e:
    print(f"Failed to import Tasks API: {e}")
