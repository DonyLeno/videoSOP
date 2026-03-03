import os
import base64
import cv2
import openai
from openai import OpenAI
import time

# Configuration
API_KEY = "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"

# User requested model: gpt5.2
# We will try it first, but fallback to gpt-4o if it fails (as 5.2 likely doesn't exist publicly yet)
MODELS_TO_TRY = [
    "gpt-5.2",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo"
]

# Paths
BASE_DIR = "/Users/ph/Documents/trae_projects/gemini 2"
PROMPT_FILE = os.path.join(BASE_DIR, "data", "ch_prompt.md")
VIDEO_FILE = os.path.join(BASE_DIR, "data", "工位1.mp4")
OUTPUT_FILE = os.path.join(BASE_DIR, "test", "result", "output_chatgpt.md")

def encode_image(image):
    """Encodes a cv2 image (numpy array) to base64 string"""
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_frames(video_path, max_frames=20):
    """
    Extracts frames from the video.
    Since GPT-4o has token limits and costs, we'll sample frames uniformly.
    """
    print(f"Extracting frames from {video_path}...")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"Video info: {total_frames} frames, {fps:.2f} fps, {duration:.2f}s duration")
    
    # Calculate step to get approx max_frames
    step = max(1, total_frames // max_frames)
    
    base64_frames = []
    frame_indices = []
    
    count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % step == 0:
            # Resize frame to reduce token usage (e.g. max 512px on long side)
            h, w = frame.shape[:2]
            scale = 512 / max(h, w)
            if scale < 1:
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                
            base64_frames.append(encode_image(frame))
            frame_indices.append(count)
            
        count += 1
        if len(base64_frames) >= max_frames:
            break
            
    cap.release()
    print(f"Extracted {len(base64_frames)} frames.")
    return base64_frames

def main():
    print("=== Starting ChatGPT Test Script ===")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Load prompt
    if not os.path.exists(PROMPT_FILE):
        print(f"Error: Prompt file not found: {PROMPT_FILE}")
        return
        
    print(f"Loading prompt from: {PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_text = f.read()
        
    # Extract frames
    if not os.path.exists(VIDEO_FILE):
        print(f"Error: Video file not found: {VIDEO_FILE}")
        return
        
    try:
        frames = extract_frames(VIDEO_FILE, max_frames=10) # 10 frames for testing to save tokens
    except Exception as e:
        print(f"Error extracting frames: {e}")
        return

    # Initialize client
    client = OpenAI(api_key=API_KEY)
    
    # Prepare messages
    # GPT-4o Vision accepts content as a list of text and image_url objects
    content = [{"type": "text", "text": prompt_text}]
    
    for b64_frame in frames:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_frame}",
                "detail": "low" # Use low detail to save tokens
            }
        })
        
    messages = [
        {"role": "system", "content": "You are an expert industrial engineer."},
        {"role": "user", "content": content}
    ]

    # Try models
    for model in MODELS_TO_TRY:
        print(f"\nAttempting to use model: {model}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            print("Success!")
            
            # Save output
            print(f"Saving output to: {OUTPUT_FILE}")
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(f"# Output from {model}\n\n")
                f.write(result)
            
            print("Done.")
            return
            
        except Exception as e:
            print(f"Model {model} failed: {e}")
            
    print("\nAll models failed.")

if __name__ == "__main__":
    main()
