# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

nvenc-server is a web-based FFmpeg video processing tool with NVIDIA NVENC GPU acceleration support. It consists of a React frontend and Python Flask backend.

## Tech Stack

- **Frontend**: React 18 + TypeScript + Tailwind CSS + Vite
- **Backend**: Python Flask with CORS support
- **Video Processing**: FFmpeg with optional NVIDIA NVENC GPU encoding

## Commands

### Frontend
```bash
npm install              # Install dependencies
npm run dev              # Start Vite dev server (port 5173)
npm run build            # TypeScript compile + Vite build
npm run check            # TypeScript type checking only
npm run lint             # ESLint check
npm run preview          # Preview production build
```

### Backend
```bash
pip install -r requirements.txt     # Install dependencies
python app.py                        # Start server (0.0.0.0:5000)
python app.py --port 5001           # Custom port
python app.py --parallel            # Allow parallel FFmpeg execution
```

## Architecture

```
React Frontend (Vite dev server :5173)
    ↓ (API proxy /api → :5000)
Flask Backend (:5000)
    ↓
FFmpeg subprocess execution
    ↓
File storage (job-based UUID directories)
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/status` | GET | System/GPU stats |
| `/upload` | POST | One-step: upload + process |
| `/upload_file` | POST | Step 1: upload only (returns job_id) |
| `/process` | POST | Step 2: process uploaded file |
| `/download/<job_id>/<filename>` | GET | Download output |

### Processing Modes

1. **One-step mode**: Single POST to `/upload` with file + command
2. **Two-step mode**: Upload once via `/upload_file`, then call `/process` multiple times with same job_id for different output formats

### FFmpeg Command Format

Commands must contain `ffmpeg`, `{input}`, and `{output}` placeholders:
```bash
ffmpeg -y -i {input} -c:v h264_nvenc -b:v 4M -c:a aac {output}
```

### Concurrency Control

- Default: Serial execution using `threading.Lock` (EXEC_LOCK)
- With `--parallel` flag: Parallel execution allowed via `nullcontext()`

## Key Files

- `app.py` - Flask backend with all API routes
- `config.py` - Configuration (STORAGE_ROOT, HOST, PORT)
- `src/App.tsx` - Main React component managing app state
- `src/components/` - UI components (FileUpload, CommandInput, ProcessControl, etc.)
- `vite.config.ts` - Vite config with API proxy to backend

## Configuration Notes

- Storage path in `config.py` is Windows-specific (`E:\\nvenc_server`); modify for other platforms
- Vite proxies `/api/*` requests to `http://127.0.0.1:5000` (strips `/api` prefix)
- CORS is open (allows all origins) - restrict in production if needed
