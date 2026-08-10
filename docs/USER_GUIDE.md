# 用户指南

## 环境准备

1. 安装 Python 3.11 x64。
2. 安装 FFmpeg，并确认 `ffmpeg -version` 和 `ffprobe -version` 可运行。
3. 在项目根目录创建虚拟环境并安装依赖。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 启动

```powershell
python -m video_script_studio
```

首次启动会检查 Python、FFmpeg 和 ffprobe。Whisper 模型不存入 Git，第一次实际转写前需要准备本地模型或允许依赖库下载模型。

