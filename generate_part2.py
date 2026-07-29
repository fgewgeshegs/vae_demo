import requests
import time

API_KEY = "sk-aRJXTb8vFxkp4KIL26URj3KNc28ZYn4Bzfsg3r0zWNxXPAJ2"
BASE_URL = "https://apihub.agnes-ai.com/v1"
GET_RESULT_URL = "https://apihub.agnes-ai.com/agnesapi"

PART2_PROMPT = (
    "A high-tech digital dashboard floating in a dark cyber-space. In the center, a glowing hexagonal core with the label 'Function'. "
    "Four distinct luminous paths extend to the edges, each ending in a futuristic icon representing modules: "
    "Top: Student Profile. Right: Intelligent Assessment. Bottom: Learning Path. Left: Resource Recommendation. "
    "Clean UI design, cyberpunk neon glow (cyan and purple), 4k resolution, smooth cinematic camera movement, holographic HUD style."
)

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "agnes-video-v2.0",
    "prompt": PART2_PROMPT,
    "height": 768,
    "width": 1152,
    "num_frames": 241,
    "frame_rate": 24
}

def main():
    print("[*] Creating Part 2 task...")
    try:
        r = requests.post(f"{BASE_URL}/videos", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        video_id = data.get("video_id")
        print(f"[+] Task created: {video_id}")
        
        while True:
            res = requests.get(f"{GET_RESULT_URL}?video_id={video_id}", headers={"Authorization": f"Bearer {API_KEY}"})
            res.raise_for_status()
            status_data = res.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            print(f"    Status: {status} | Progress: {progress}%", end="\r")
            
            if status == "completed":
                url = status_data.get("url")
                if url:
                    print(f"\n[+] Downloading...")
                    with requests.get(url, stream=True) as dl:
                        dl.raise_for_status()
                        with open("part2_functions.mp4", "wb") as f:
                            for chunk in dl.iter_content(chunk_size=8192):
                                f.write(chunk)
                    print("[+] Saved part2_functions.mp4")
                break
            elif status == "failed":
                print(f"\n[!] Task failed.")
                break
            
            time.sleep(5)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        if hasattr(e, 'response'):
            print(e.response.text)

if __name__ == "__main__":
    main()
