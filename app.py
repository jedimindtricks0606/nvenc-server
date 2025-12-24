# nvenc-server Flask application
# Features:
# - Default host/port from config: HOST=0.0.0.0, PORT=5000
# - Command-line options:
#   --port <int>        Override server port (default from config.py)
#   --parallel          Allow multiple FFmpeg tasks to run in parallel
#                       (by default tasks run serially to avoid resource contention)
# - Concurrency control:
#   When parallel is disabled, FFmpeg execution is wrapped by a global lock (EXEC_LOCK)
#   When parallel is enabled, the lock is bypassed using contextlib.nullcontext
# - Responses include duration_ms for both success and error, measuring end-to-end FFmpeg time
import os
import uuid
import shlex
import subprocess
import time
import threading
import argparse
from contextlib import nullcontext
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import STORAGE_ROOT, HOST, PORT, ensure_storage_root
import platform
import psutil
import shutil
import importlib

ensure_storage_root()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
EXEC_LOCK = threading.Lock()
ALLOW_PARALLEL = False

def make_job_dir():
    job_id = uuid.uuid4().hex
    job_dir = Path(STORAGE_ROOT) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir
def get_job_dir(job_id):
    p = Path(STORAGE_ROOT) / job_id
    return p if p.exists() and p.is_dir() else None
def find_input_file(job_dir: Path):
    for p in job_dir.iterdir():
        if p.is_file() and p.name.startswith("input"):
            return p
    return None

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

@app.route("/status", methods=["GET"])
def status():
    sys = platform.system()
    cpu_percent = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    mem = {
        "total": vm.total,
        "used": vm.used,
        "available": vm.available,
        "percent": vm.percent,
    }
    gpus = []
    try:
        pynvml = importlib.import_module("pynvml")
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            try:
                name = name.decode() if isinstance(name, (bytes, bytearray)) else str(name)
            except Exception:
                name = str(name)
            uuid = pynvml.nvmlDeviceGetUUID(h)
            try:
                uuid = uuid.decode() if isinstance(uuid, (bytes, bytearray)) else str(uuid)
            except Exception:
                uuid = str(uuid)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(h)
            try:
                enc_util, _ = pynvml.nvmlDeviceGetEncoderUtilization(h)
            except Exception:
                enc_util = None
            try:
                dec_util, _ = pynvml.nvmlDeviceGetDecoderUtilization(h)
            except Exception:
                dec_util = None
            gpus.append({
                "index": i,
                "name": name,
                "uuid": uuid,
                "utilization_percent": float(getattr(util, "gpu", 0.0)),
                "memory_used_mb": round(float(meminfo.used) / (1024 * 1024), 2),
                "memory_total_mb": round(float(meminfo.total) / (1024 * 1024), 2),
                "encoder_utilization_percent": enc_util,
                "decoder_utilization_percent": dec_util,
            })
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
    except Exception:
        if shutil.which("nvidia-smi"):
            encdec = {}
            try:
                dmon = subprocess.check_output(["nvidia-smi", "dmon", "-c", "1", "-s", "u"], text=True, stderr=subprocess.DEVNULL)
                for line in dmon.strip().splitlines():
                    if not line or line.startswith("#"):
                        continue
                    cols = [c for c in line.split() if c]
                    if len(cols) >= 5:
                        try:
                            idx = int(cols[0])
                            enc = float(cols[3])
                            dec = float(cols[4])
                            encdec[idx] = (enc, dec)
                        except Exception:
                            pass
            except Exception:
                encdec = {}
            try:
                q = ["nvidia-smi", "--query-gpu=index,name,uuid,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"]
                out = subprocess.check_output(q, text=True, stderr=subprocess.DEVNULL)
                for line in out.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 6:
                        idx = int(parts[0])
                        enc, dec = encdec.get(idx, (None, None))
                        gpus.append({
                            "index": idx,
                            "name": parts[1],
                            "uuid": parts[2],
                            "utilization_percent": float(parts[3]),
                            "memory_used_mb": float(parts[4]),
                            "memory_total_mb": float(parts[5]),
                            "encoder_utilization_percent": enc,
                            "decoder_utilization_percent": dec,
                        })
            except Exception:
                gpus = []
    return jsonify({
        "status": "ok",
        "system": sys,
        "cpu_percent": cpu_percent,
        "memory": mem,
        "gpus": gpus,
    })
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
    print(f"[upload] received command: {command}")
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
        print(f"[upload] executing: {shlex.join(cmd)}")
    except Exception:
        print(f"[upload] executing: {' '.join(cmd)}")
    try:
        ctx = nullcontext() if ALLOW_PARALLEL else EXEC_LOCK
        with ctx:
            start = time.perf_counter()
            r = subprocess.run(cmd, capture_output=True, text=True)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
    except Exception as e:
        return jsonify({"status": "error", "message": "execution failed", "detail": str(e)}), 500
    if r.returncode != 0:
        return jsonify({"status": "error", "message": "ffmpeg failed", "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode, "duration_ms": elapsed_ms}), 500
    download_path = url_for("download", job_id=job_id, filename=output_path.name)
    return jsonify({"status": "success", "message": "ok", "job_id": job_id, "input": input_path.name, "output": output_path.name, "download_path": download_path, "duration_ms": elapsed_ms})

@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "missing file"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"status": "error", "message": "empty filename"}), 400
    job_id, job_dir = make_job_dir()
    original = secure_filename(file.filename)
    ext = Path(original).suffix or ".mp4"
    input_name = f"input{ext}"
    input_path = job_dir / input_name
    file.save(str(input_path))
    return jsonify({"status": "success", "message": "ok", "job_id": job_id, "input": input_path.name})

@app.route("/process", methods=["POST"])
def process():
    job_id = request.form.get("job_id") or request.values.get("job_id") or (request.json.get("job_id") if request.is_json and request.json else None)
    command = request.form.get("command") or request.values.get("command") or (request.json.get("command") if request.is_json and request.json else None) or request.headers.get("X-Command")
    output_filename = request.form.get("output_filename") or (request.json.get("output_filename") if request.is_json else None) or "output.mp4"
    if not job_id:
        return jsonify({"status": "error", "message": "missing job_id"}), 400
    job_dir = get_job_dir(job_id)
    if not job_dir:
        return jsonify({"status": "error", "message": "invalid job_id"}), 404
    input_path = find_input_file(job_dir)
    if not input_path:
        return jsonify({"status": "error", "message": "missing input file in job"}), 400
    if not command:
        return jsonify({"status": "error", "message": "missing command"}), 400
    if not validate_command(command):
        return jsonify({"status": "error", "message": "invalid command, require ffmpeg with {input} and {output}"}), 400
    output_path = job_dir / secure_filename(output_filename)
    cmd = build_command(command, input_path, output_path)
    if not cmd:
        return jsonify({"status": "error", "message": "failed to build command"}), 400
    try:
        print(f"[process] job={job_id} executing: {shlex.join(cmd)}")
    except Exception:
        print(f"[process] job={job_id} executing: {' '.join(cmd)}")
    try:
        ctx = nullcontext() if ALLOW_PARALLEL else EXEC_LOCK
        with ctx:
            start = time.perf_counter()
            r = subprocess.run(cmd, capture_output=True, text=True)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
    except Exception as e:
        return jsonify({"status": "error", "message": "execution failed", "detail": str(e)}), 500
    if r.returncode != 0:
        return jsonify({"status": "error", "message": "ffmpeg failed", "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode, "duration_ms": elapsed_ms}), 500
    download_path = url_for("download", job_id=job_id, filename=output_path.name)
    return jsonify({"status": "success", "message": "ok", "job_id": job_id, "input": input_path.name, "output": output_path.name, "download_path": download_path, "duration_ms": elapsed_ms})

@app.route("/download/<job_id>/<filename>", methods=["GET"])
def download(job_id, filename):
    directory = Path(STORAGE_ROOT) / job_id
    if not directory.exists():
        return jsonify({"error": "not found"}), 404
    return send_from_directory(str(directory), filename, as_attachment=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="nvenc-server")
    parser.add_argument("--port", type=int, default=PORT, help="Server port (default from config)")
    parser.add_argument("--parallel", action="store_true", help="Allow multiple FFmpeg tasks in parallel")
    args = parser.parse_args()
    ALLOW_PARALLEL = args.parallel
    app.run(host=HOST, port=args.port)

