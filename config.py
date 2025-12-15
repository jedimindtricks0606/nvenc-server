import os

STORAGE_ROOT = r"E:\\nvenc_server"
HOST = "0.0.0.0"
PORT = 5000

def ensure_storage_root():
    os.makedirs(STORAGE_ROOT, exist_ok=True)

