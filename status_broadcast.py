#!/usr/bin/env python3
"""
System Status UDP Broadcaster

Periodically broadcasts system status (CPU, memory, GPU, disk, network) via UDP.
Default: port 9999, interval 2 seconds.

Usage:
    python status_broadcast.py                    # Default settings
    python status_broadcast.py --port 9998        # Custom port
    python status_broadcast.py --interval 5       # 5 second interval
    python status_broadcast.py --address 192.168.1.255  # Custom broadcast address
"""

import argparse
import json
import platform
import shutil
import socket
import subprocess
import time
from datetime import datetime

import psutil


def get_cpu_info():
    """Get CPU usage and frequency info."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)

    freq = psutil.cpu_freq()
    freq_info = None
    if freq:
        freq_info = {
            "current_mhz": round(freq.current, 2),
            "min_mhz": round(freq.min, 2) if freq.min else None,
            "max_mhz": round(freq.max, 2) if freq.max else None,
        }

    # Per-CPU usage
    per_cpu = psutil.cpu_percent(interval=0, percpu=True)

    return {
        "percent": cpu_percent,
        "count_logical": cpu_count_logical,
        "count_physical": cpu_count_physical,
        "frequency": freq_info,
        "per_cpu_percent": per_cpu,
    }


def get_memory_info():
    """Get memory and swap usage."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total_mb": round(vm.total / (1024 * 1024), 2),
        "used_mb": round(vm.used / (1024 * 1024), 2),
        "available_mb": round(vm.available / (1024 * 1024), 2),
        "percent": vm.percent,
        "swap_total_mb": round(swap.total / (1024 * 1024), 2),
        "swap_used_mb": round(swap.used / (1024 * 1024), 2),
        "swap_percent": swap.percent,
    }


def get_disk_info():
    """Get disk usage for main partitions."""
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue
    return disks


def get_network_info():
    """Get network I/O statistics."""
    net = psutil.net_io_counters()
    return {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "errin": net.errin,
        "errout": net.errout,
    }


def get_gpu_info():
    """Get NVIDIA GPU info using pynvml or nvidia-smi."""
    gpus = []

    # Try pynvml first
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()

        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)

            name = pynvml.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, (bytes, bytearray)) else str(name)

            gpu_uuid = pynvml.nvmlDeviceGetUUID(h)
            gpu_uuid = gpu_uuid.decode() if isinstance(gpu_uuid, (bytes, bytearray)) else str(gpu_uuid)

            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(h)

            # Temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None

            # Power
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0  # mW to W
            except Exception:
                power = None

            try:
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(h) / 1000.0
            except Exception:
                power_limit = None

            # Encoder/decoder utilization
            try:
                enc_util, _ = pynvml.nvmlDeviceGetEncoderUtilization(h)
            except Exception:
                enc_util = None

            try:
                dec_util, _ = pynvml.nvmlDeviceGetDecoderUtilization(h)
            except Exception:
                dec_util = None

            # Fan speed
            try:
                fan = pynvml.nvmlDeviceGetFanSpeed(h)
            except Exception:
                fan = None

            gpus.append({
                "index": i,
                "name": name,
                "uuid": gpu_uuid,
                "utilization_percent": float(getattr(util, "gpu", 0)),
                "memory_utilization_percent": float(getattr(util, "memory", 0)),
                "memory_used_mb": round(meminfo.used / (1024 * 1024), 2),
                "memory_total_mb": round(meminfo.total / (1024 * 1024), 2),
                "memory_free_mb": round(meminfo.free / (1024 * 1024), 2),
                "temperature_c": temp,
                "power_w": round(power, 2) if power else None,
                "power_limit_w": round(power_limit, 2) if power_limit else None,
                "encoder_utilization_percent": enc_util,
                "decoder_utilization_percent": dec_util,
                "fan_speed_percent": fan,
            })

        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

        return gpus
    except Exception:
        pass

    # Fallback to nvidia-smi
    if not shutil.which("nvidia-smi"):
        return gpus

    encdec = {}
    try:
        dmon = subprocess.check_output(
            ["nvidia-smi", "dmon", "-c", "1", "-s", "u"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
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
        pass

    try:
        query = [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,utilization.gpu,utilization.memory,memory.used,memory.total,memory.free,temperature.gpu,power.draw,power.limit,fan.speed",
            "--format=csv,noheader,nounits"
        ]
        out = subprocess.check_output(query, text=True, stderr=subprocess.DEVNULL, timeout=5)

        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 8:
                idx = int(parts[0])
                enc, dec = encdec.get(idx, (None, None))

                def safe_float(val):
                    try:
                        if val in ("[Not Supported]", "[N/A]", ""):
                            return None
                        return float(val)
                    except:
                        return None

                gpus.append({
                    "index": idx,
                    "name": parts[1],
                    "uuid": parts[2],
                    "utilization_percent": safe_float(parts[3]),
                    "memory_utilization_percent": safe_float(parts[4]),
                    "memory_used_mb": safe_float(parts[5]),
                    "memory_total_mb": safe_float(parts[6]),
                    "memory_free_mb": safe_float(parts[7]) if len(parts) > 7 else None,
                    "temperature_c": safe_float(parts[8]) if len(parts) > 8 else None,
                    "power_w": safe_float(parts[9]) if len(parts) > 9 else None,
                    "power_limit_w": safe_float(parts[10]) if len(parts) > 10 else None,
                    "fan_speed_percent": safe_float(parts[11]) if len(parts) > 11 else None,
                    "encoder_utilization_percent": enc,
                    "decoder_utilization_percent": dec,
                })
    except Exception:
        pass

    return gpus


def get_uptime():
    """Get system uptime in seconds."""
    return time.time() - psutil.boot_time()


def get_load_average():
    """Get system load average (Unix-like systems)."""
    try:
        load = psutil.getloadavg()
        return {
            "1min": round(load[0], 2),
            "5min": round(load[1], 2),
            "15min": round(load[2], 2),
        }
    except (AttributeError, OSError):
        return None


def collect_status():
    """Collect all system status information."""
    hostname = socket.gethostname()

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "hostname": hostname,
        "system": platform.system(),
        "platform": platform.platform(),
        "uptime_seconds": round(get_uptime(), 2),
        "load_average": get_load_average(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "gpus": get_gpu_info(),
    }


def broadcast_status(sock, address, port):
    """Collect and broadcast status once."""
    status = collect_status()
    data = json.dumps(status, ensure_ascii=False).encode("utf-8")
    sock.sendto(data, (address, port))
    return len(data), status


def main():
    parser = argparse.ArgumentParser(description="System Status UDP Broadcaster")
    parser.add_argument("--port", type=int, default=9999, help="UDP broadcast port (default: 9999)")
    parser.add_argument("--interval", type=float, default=2.0, help="Broadcast interval in seconds (default: 2)")
    parser.add_argument("--address", type=str, default="255.255.255.255", help="Broadcast address (default: 255.255.255.255)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"Starting status broadcast to {args.address}:{args.port} every {args.interval}s")
    print("Press Ctrl+C to stop")

    try:
        while True:
            try:
                size, status = broadcast_status(sock, args.address, args.port)
                cpu = status["cpu"]["percent"]
                mem = status["memory"]["percent"]
                gpu_info = ""
                if status["gpus"]:
                    gpu = status["gpus"][0]
                    gpu_info = f" | GPU: {gpu['utilization_percent']}%"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent {size} bytes | CPU: {cpu}% | MEM: {mem}%{gpu_info}")
            except Exception as e:
                print(f"Error: {e}")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
