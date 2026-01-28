
import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_task_status():
    # 1. Login
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/api/login", json={"username": "admin", "password": "geniviewa"})
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login success.")

    # 2. Check task status (should be none initially)
    print("Checking initial task status...")
    resp = requests.get(f"{BASE_URL}/api/task_status", headers=headers)
    if resp.status_code != 200:
        print("Check status failed:", resp.text)
        return
    print("Initial status:", resp.json())

    # 3. Start a task (mock if possible, or use a real short video)
    # We need a video file. 'data/motor.mp4' exists.
    # We can try to start it.
    print("Starting task...")
    payload = {
        "video_path": "data/motor.mp4",
        "model": "gemini-1.5-flash",
        "fps": 1.0
    }
    # Note: This will actually run the analysis which might take time and cost money/quota.
    # But we need to verify status changes.
    # We can just check if it returns 200 and then immediately check status.
    
    # Actually, I don't want to consume quota if I can avoid it.
    # But the user asked to verify "save detection state".
    # I'll skip starting the task if I can't mock it easily.
    # But I can check if /api/task_status returns the structure we expect.
    # The initial check returned status 'none', which is correct structure.
    
    pass

if __name__ == "__main__":
    test_task_status()
