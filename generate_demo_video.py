import requests
import time
import json
import sys

# Agnes AI API Configuration
API_KEY = "sk-aRJXTb8vFxkp4KIL26URj3KNc28ZYn4Bzfsg3r0zWNxXPAJ2"
BASE_URL = "https://apihub.agnes-ai.com/v1"
GET_RESULT_URL = "https://apihub.agnes-ai.com/agnesapi"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Video Prompts
PART1_PROMPT = (
    "A futuristic digital space filled with chaotic, glowing blue data streams and fragmented text elements, "
    "representing information overload. The scene transitions to an abstract broken digital grid with red warning signals, "
    "symbolizing a disconnect in knowledge. Volumetric lighting, 4k resolution, dark cinematic atmosphere, high-tech style."
)

PART2_PROMPT = (
    "A high-tech digital dashboard floating in a dark cyber-space. In the center, a glowing hexagonal core with the label 'Function'. "
    "Four distinct luminous paths extend to the edges, each ending in a futuristic icon representing modules: "
    "Top: Student Profile. Right: Intelligent Assessment. Bottom: Learning Path. Left: Resource Recommendation. "
    "Clean UI design, cyberpunk neon glow (cyan and purple), 4k resolution, smooth cinematic camera movement, holographic HUD style."
)

def create_video_task(prompt, filename_hint, retries=3):
    """Create a video generation task with retry logic for 503 errors."""
    payload = {
        "model": "agnes-video-v2.0",
        "prompt": prompt,
        "height": 768,
        "width": 1152,
        "num_frames": 241,  # Approx 10 seconds at 24fps
        "frame_rate": 24
    }
    
    print(f"[*] Creating task for {filename_hint}...")
    for attempt in range(retries):
        try:
            response = requests.post(f"{BASE_URL}/videos", headers=HEADERS, json=payload)
            if response.status_code == 503:
                print(f"    Service busy (503), retrying in 10s... (Attempt {attempt + 1}/{retries})")
                time.sleep(10)
                continue
            response.raise_for_status()
            data = response.json()
            print(f"[+] Task created: {data.get('video_id')}")
            return data
        except Exception as e:
            if attempt == retries - 1:
                print(f"[!] Error creating task after {retries} attempts: {e}")
                if hasattr(e, 'response') and e.response:
                    print(e.response.text)
                return None
            print(f"    Retrying in 5s... ({e})")
            time.sleep(5)
    return None

def poll_video_result(video_id, filename_hint):
    """Poll for video completion and download."""
    print(f"[*] Waiting for {filename_hint} ({video_id})...")
    while True:
        try:
            # Recommended method: GET /agnesapi?video_id=<VIDEO_ID>
            response = requests.get(
                f"{GET_RESULT_URL}?video_id={video_id}", 
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            progress = data.get("progress", 0)
            
            print(f"    Status: {status} | Progress: {progress}%", end="\r")
            
            if status == "completed":
                video_url = data.get("url")
                if video_url:
                    print(f"\n[+] Downloading {filename_hint}...")
                    download_video(video_url, f"{filename_hint}.mp4")
                    return True
                else:
                    print(f"\n[!] Completed but no URL found.")
                    return False
            elif status == "failed":
                print(f"\n[!] Task failed: {data.get('error')}")
                return False
            
            time.sleep(5)  # Wait 5 seconds before next poll
        except Exception as e:
            print(f"\n[!] Error polling: {e}")
            time.sleep(10)

def download_video(url, filename):
    """Download the video from URL."""
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"[+] Saved: {filename}")
    except Exception as e:
        print(f"[!] Download failed: {e}")

def main():
    # 1. Create Part 1 (Bottlenecks)
    task1 = create_video_task(PART1_PROMPT, "part1_bottlenecks")
    
    # Wait for a bit before creating the second task to avoid rate limiting
    if task1:
        print("[*] Waiting 30s before creating Part 2 to avoid rate limits...")
        time.sleep(30)
        
        # 2. Create Part 2 (System Functions)
        task2 = create_video_task(PART2_PROMPT, "part2_functions")
    else:
        task2 = None

    # Poll Part 1
    if task1:
        poll_video_result(task1.get("video_id"), "part1_bottlenecks")
        
    # Poll Part 2 (if it was created)
    if task2:
        poll_video_result(task2.get("video_id"), "part2_functions")
    elif not task1:
        print("[!] No tasks were successfully created.")
    
    print("\n[OK] Video generation process finished.")

if __name__ == "__main__":
    main()
