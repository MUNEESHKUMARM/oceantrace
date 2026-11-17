import os
import time
import urllib.request

url = "https://zenodo.org/api/records/13761290/files/02_Test_images_and_ground_truth.7z/content"
dest_dir = "g:/SIH/oceantrace-ai/backend/data/dataset_audit"
os.makedirs(dest_dir, exist_ok=True)
dest_path = os.path.join(dest_dir, "02_Test_images_and_ground_truth.7z")

req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

existing_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
print(f"Existing size: {existing_size} bytes")

req = urllib.request.Request(url, headers=req_headers)
if existing_size > 0:
    req.add_header('Range', f'bytes={existing_size}-')

print("Starting download of Part III test archive...")
start_time = time.time()
bytes_downloaded = 0

try:
    with urllib.request.urlopen(req) as resp:
        mode = 'ab' if existing_size > 0 and resp.status == 206 else 'wb'
        if mode == 'wb':
            existing_size = 0
        
        total_size = existing_size + int(resp.headers.get('Content-Length', 0))
        print(f"Target size: {total_size} bytes ({total_size/(1024**3):.2f} GB), mode: {mode}")
        
        with open(dest_path, mode) as out:
            while True:
                chunk = resp.read(1024 * 1024) # 1MB chunk
                if not chunk:
                    break
                out.write(chunk)
                bytes_downloaded += len(chunk)
                current_size = existing_size + bytes_downloaded
                elapsed = time.time() - start_time
                speed_mb = (bytes_downloaded / (1024 * 1024)) / (elapsed + 1e-5)
                pct = (current_size / total_size) * 100 if total_size > 0 else 0
                if bytes_downloaded % (50 * 1024 * 1024) < (1024 * 1024):
                    print(f"Progress: {current_size/(1024**3):.2f}/{total_size/(1024**3):.2f} GB ({pct:.1f}%) | Speed: {speed_mb:.2f} MB/s | Elapsed: {elapsed:.1f}s")
                # Stop after 2 GB downloaded for audit sample if needed, or let it finish if fast
                if bytes_downloaded >= 1500 * 1024 * 1024:
                    print("Reached 1.5 GB downloaded chunk for audit sampling.")
                    break
except Exception as e:
    print(f"Download error: {e}")

print(f"Final file size: {os.path.getsize(dest_path)} bytes")
