
import os
import json
from openai import OpenAI

def load_api_key():
    if os.environ.get("MOONSHOT_API_KEY"):
        return os.environ["MOONSHOT_API_KEY"]
    try:
        with open("test/apikey.md", "r") as f:
            return f.read().strip()
    except:
        return None

def test():
    api_key = load_api_key()
    if not api_key:
        print("No API Key found")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    
    img_path = "data/full/frame_00001_0.00.jpg"
    if not os.path.exists(img_path):
        # Try to find any jpg in data
        for root, dirs, files in os.walk("data"):
            for f in files:
                if f.endswith(".jpg"):
                    img_path = os.path.join(root, f)
                    break
            if img_path != "data/full/frame_00001_0.00.jpg":
                break
    
    if not os.path.exists(img_path):
        print("No image found to test")
        return

    print(f"Uploading {img_path}...")
    # server.py uses purpose="image"
    with open(img_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="file-extract")
    
    file_id = file_obj.id
    print(f"Uploaded. File ID: {file_id}")

    # Try Kimi 2.5 model if available, or moonshot-v1-8k
    model = "kimi-2.5" 

    print("Trying to use file_id in chat...")
    
    # Attempt 1: Raw ID in image_url
    try:
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this image."},
                {"type": "image_url", "image_url": {"url": file_id}}
            ]}
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=messages
        )
        print("Attempt 1 (Raw ID) Response:", resp.choices[0].message.content)
    except Exception as e:
        print("Attempt 1 (Raw ID) Failed:", e)

if __name__ == "__main__":
    test()
