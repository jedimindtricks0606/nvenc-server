# nvenc-server 使用说明

- 后端：Flask（端口 `5000`），存储根目录 `E:\nvenc_server`
- 前端：Vite 开发服务器（默认端口 `5173`），通过代理 `/api` 调用后端

## 启动
- 安装后端依赖：`pip install -r requirements.txt`
- 启动后端：`python app.py`（监听 `0.0.0.0:5000`）
- 启动前端开发服务器：`npm run dev -- --host --port 5173 --strictPort`

### 启动参数
- 指定端口（默认 `5000` 来自 `config.py`）：
  - `python app.py --port 5001`
- 允许并行执行多个导出任务（默认串行）：
  - `python app.py --parallel`
- 示例（自定义端口并开启并行）：
  - `python app.py --port 5001 --parallel`

## 健康检查
- `GET` `http://<后端IP>:5000/health` → `{"status":"ok"}`

## 一体化模式（单次上传并处理）
- `POST` `http://<后端IP>:5000/upload`
- 表单字段：
  - `file`：视频文件
  - `command`：以 `ffmpeg` 开头，必须包含 `{input}` 与 `{output}`
  - `output_filename`：可选，默认 `output.mp4`
- 成功响应：
  - `{"status":"success","message":"ok","job_id":"...","input":"input.mp4","output":"out.mp4","download_path":"/download/<job_id>/out.mp4","duration_ms":1234}`

## 分步模式（避免重复上传）
### 步骤1：上传源文件
- `POST` `http://<后端IP>:5000/upload_file`
- 表单字段：
  - `file`：视频文件
- 成功响应：
  - `{"status":"success","message":"ok","job_id":"...","input":"input.mp4"}`

### 步骤2：提交多次处理任务
- `POST` `http://<后端IP>:5000/process`
- 表单字段：
  - `job_id`：步骤1返回的 `job_id`
  - `command`：FFmpeg命令（包含 `{input}` 与 `{output}`）
  - `output_filename`：导出文件名
- 成功响应：
  - `{"status":"success","message":"ok","job_id":"...","input":"input.mp4","output":"out.mp4","download_path":"/download/<job_id>/out.mp4","duration_ms":1234}`

## 下载
- `GET` `http://<后端IP>:5000/download/<job_id>/<filename>`
- 返回处理好的文件作为附件

## 命令示例
- `ffmpeg -y -i {input} -c:v h264_nvenc -b:v 4M -c:a aac {output}`
- `ffmpeg -y -i {input} -c:v libx264 -crf 23 -c:a aac {output}`

## curl 示例
```bash
# 步骤1：上传源文件
curl -X POST -F "file=@/path/to/video.mp4" http://<后端IP>:5000/upload_file

# 步骤2：提交处理任务
curl -X POST -F "job_id=<job_id>" \
     -F "command=ffmpeg -y -i {input} -c:v h264_nvenc -b:v 4M -c:a aac {output}" \
     -F "output_filename=out.mp4" \
     http://<后端IP>:5000/process

# 下载
curl -O "http://<后端IP>:5000/download/<job_id>/out.mp4"
```

## 说明
- 返回 `duration_ms` 表示导出耗时，成功与失败均包含。
- 若未安装 FFmpeg 或 PATH 未配置，处理会失败并在 `stderr` 中给出原因。
- 分步模式下，可在同一 `job_id` 下提交多次处理任务，无需重复上传。
