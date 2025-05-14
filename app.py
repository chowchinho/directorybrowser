from flask import Flask, request, jsonify, send_from_directory
import os
import threading
import time

app = Flask(__name__, static_folder='.')

# Base directories to scan
BASE_DIRS = [
    "{{DIR1}}",
    "{{DIR2}}"
]

# Folder cache and timestamp
folder_cache = []
last_scanned = None

# Cache builder (max depth: 1)
def build_folder_cache():
    global folder_cache, last_scanned
    folder_cache = []
    print("Scanning folders (max depth: 1)...")

    for base_dir in BASE_DIRS:
        base_depth = base_dir.rstrip(os.sep).count(os.sep)

        for root, dirs, _ in os.walk(base_dir):
            current_depth = root.rstrip(os.sep).count(os.sep)

            # Stop walking if current depth exceeds 1 level from base
            if current_depth - base_depth >= 1:
                dirs.clear()
                continue

            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                folder_cache.append(full_path)

    last_scanned = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Folder cache built with {len(folder_cache)} entries at {last_scanned}.")
    for path in folder_cache:
        print("Cached:", path)
        
@app.route("/status")
def status():
    return jsonify({"last_scanned": last_scanned})

# Search API
@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    matches = [path for path in folder_cache if query in path.lower()]
    return jsonify(matches)

# Manual refresh API
@app.route("/refresh", methods=["POST"])
def refresh_cache():
    threading.Thread(target=build_folder_cache).start()
    return jsonify({"status": "refresh started", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
    
@app.route("/base_dirs")
def get_base_dirs():
    return jsonify(BASE_DIRS)

@app.route("/list_subfolders")
def list_subfolders():
    selected_dir = request.args.get("dir")
    if not selected_dir or selected_dir not in BASE_DIRS:
        return jsonify([])

    try:
        subfolders = []
        with os.scandir(selected_dir) as entries:
            for entry in entries:
                if entry.is_dir():
                    full_path = os.path.join(selected_dir, entry.name)
                    mtime = entry.stat().st_mtime
                    subfolders.append((full_path, mtime))

        # Sort by last modified time (newest first)
        subfolders.sort(key=lambda x: x[1], reverse=True)

        return jsonify([path for path, _ in subfolders])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve the frontend
@app.route("/")
def index():
    return send_from_directory('.', 'index.html')

if __name__ == "__main__":
    build_folder_cache()

    # Scheduled re-scan every 6 hours
    def refresh_cache_loop():
        while True:
            time.sleep(21600)
            build_folder_cache()

    threading.Thread(target=refresh_cache_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
