import os
import uuid
import shlex
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import STORAGE_ROOT, HOST, PORT, ensure_storage_root

ensure_storage_root()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

def make_job_dir():
    job_id = uuid.uuid4().hex
    job_dir = Path(STORAGE_ROOT) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir

def validate_command(cmd):
    s = cmd.strip()
    return "ffmpeg" in s.split()[0].lower() and ("{input}" in s and "{output}" in s)

def build_command(cmd, input_path, output_path):
    tokens = shlex.split(cmd, posix=True)
    if not tokens:
        return None
    tokens[0] = "ffmpeg"
    built = []
    for t in tokens:
        if t == "{input}":
            built.append(str(input_path))
        elif t == "{output}":
            built.append(str(output_path))
        else:
            built.append(t)
    return built

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "missing file"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"status": "error", "message": "empty filename"}), 400
    # Robustly extract command from multiple sources
    command = (
        request.form.get("command")
        or request.values.get("command")
        or (request.json.get("command") if request.is_json and request.json else None)
        or request.headers.get("X-Command")
    )
    if not command:
        return jsonify({"status": "error", "message": "missing command", "form_keys": list(request.form.keys()), "content_type": request.content_type}), 400
    if not validate_command(command):
        return jsonify({"status": "error", "message": "invalid command, require ffmpeg with {input} and {output}"}), 400
    output_filename = request.form.get("output_filename") or (request.json.get("output_filename") if request.is_json else None) or "output.mp4"
    job_id, job_dir = make_job_dir()
    original = secure_filename(file.filename)
    ext = Path(original).suffix or ".mp4"
    input_name = f"input{ext}"
    input_path = job_dir / input_name
    output_path = job_dir / secure_filename(output_filename)
    file.save(str(input_path))
    cmd = build_command(command, input_path, output_path)
    if not cmd:
        return jsonify({"status": "error", "message": "failed to build command"}), 400
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return jsonify({"status": "error", "message": "execution failed", "detail": str(e)}), 500
    if r.returncode != 0:
        return jsonify({"status": "error", "message": "ffmpeg failed", "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}), 500
    download_path = url_for("download", job_id=job_id, filename=output_path.name)
    return jsonify({"status": "success", "message": "ok", "job_id": job_id, "input": input_path.name, "output": output_path.name, "download_path": download_path})

@app.route("/download/<job_id>/<filename>", methods=["GET"])
def download(job_id, filename):
    directory = Path(STORAGE_ROOT) / job_id
    if not directory.exists():
        return jsonify({"error": "not found"}), 404
    return send_from_directory(str(directory), filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)

