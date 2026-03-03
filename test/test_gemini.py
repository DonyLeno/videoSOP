import os
import time
import sys
import traceback
from typing import List, Any, Optional

# Configuration
API_KEY = "AIzaSyCjlG2oWMfGLPRZsWhCY9JeDhaD_4yIMZg"

# User requested models: 3.1 pro -> 3.0. 
# Based on available models in this environment:
MODELS_TO_TRY = [
    "gemini-3.1-pro-preview", 
    "gemini-3-pro-preview", 
]

# Paths - absolute paths to avoid issues
BASE_DIR = "/Users/ph/Documents/trae_projects/gemini 2"
PROMPT_FILE = os.path.join(BASE_DIR, "data", "ch_prompt.md")
VIDEO_FILE = os.path.join(BASE_DIR, "data", "工位1.mp4")
OUTPUT_FILE = os.path.join(BASE_DIR, "test", "result", "output.md")

def get_client():
    try:
        from google import genai
        return genai.Client(api_key=API_KEY)
    except ImportError:
        print("Error: 'google-genai' package not found. Please install it.")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)

def upload_video(client, path: str) -> Any:
    print(f"Uploading video: {path}...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Video file not found: {path}")
    
    # Upload the file
    try:
        # Check if we can use the high-level upload
        if hasattr(client, "files") and hasattr(client.files, "upload"):
            # Try 'file' argument which is standard in newer SDKs
            try:
                # Open file in binary mode to avoid path encoding issues in headers
                with open(path, "rb") as f:
                    video_file = client.files.upload(
                        file=f,
                        config={"display_name": "station1_video", "mime_type": "video/mp4"}
                    )
            except TypeError:
                # Fallback if 'file' kwarg fails, try to use path but rename first to avoid ascii error
                print("Fallback: Renaming file to avoid encoding issues...")
                ascii_path = os.path.join(os.path.dirname(path), "station1_temp.mp4")
                import shutil
                shutil.copy(path, ascii_path)
                try:
                    video_file = client.files.upload(path=ascii_path)
                except TypeError:
                    # Try positional if path kwarg fails
                     video_file = client.files.upload(ascii_path)
                finally:
                    if os.path.exists(ascii_path):
                        os.remove(ascii_path)
        else:
            # Fallback for older SDK versions or different structures
            print("Warning: client.files.upload not found. Trying alternative...")
            import google.generativeai as genai_old
            genai_old.configure(api_key=API_KEY)
            # For older SDK, we might need to copy file to ascii name
            ascii_path = os.path.join(os.path.dirname(path), "station1_temp.mp4")
            import shutil
            shutil.copy(path, ascii_path)
            try:
                video_file = genai_old.upload_file(ascii_path)
            finally:
                if os.path.exists(ascii_path):
                    os.remove(ascii_path)
            
        print(f"Upload complete. URI: {video_file.uri}")
        print(f"Name: {video_file.name}")
        return video_file
    except Exception as e:
        print(f"Upload failed: {e}")
        raise

def wait_for_active(client, file_obj):
    print("Waiting for video processing...")
    name = file_obj.name
    
    while True:
        try:
            if hasattr(client, "files") and hasattr(client.files, "get"):
                remote_file = client.files.get(name=name)
                state = str(remote_file.state)
            else:
                import google.generativeai as genai_old
                remote_file = genai_old.get_file(name)
                state = str(remote_file.state.name)
                
            print(f"State: {state}")
            if "ACTIVE" in state:
                return remote_file
            elif "FAILED" in state:
                raise RuntimeError(f"Video processing failed. State: {state}")
                
            time.sleep(5)
        except Exception as e:
            print(f"Error checking status: {e}")
            raise

def main():
    print("=== Starting Gemini Test Script ===")
    client = get_client()
    
    # 1. Load Prompt
    print(f"Loading prompt from: {PROMPT_FILE}")
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    except Exception as e:
        print(f"Failed to load prompt: {e}")
        return

    # 2. Upload Video
    try:
        video_file_obj = upload_video(client, VIDEO_FILE)
        video_file_obj = wait_for_active(client, video_file_obj)
    except Exception as e:
        print(f"Failed to process video: {e}")
        traceback.print_exc()
        return

    # 3. Generate Content with Fallback
    contents = [prompt_text, video_file_obj]
    
    success = False
    for model_name in MODELS_TO_TRY:
        print(f"\nAttempting to use model: {model_name}")
        try:
            # New SDK usage
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config={
                    "response_mime_type": "text/plain",
                }
            )
            
            print("Response received successfully.")
            result_text = response.text if hasattr(response, "text") else str(response)
            
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(result_text)
            print(f"Result saved to: {OUTPUT_FILE}")
            success = True
            break
            
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            # Continue to next model
    
    if not success:
        print("\nAll models failed.")

if __name__ == "__main__":
    main()
