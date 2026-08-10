# VideoScript Studio

Windows 本地视频文案处理工具。一期目标是使用 CPU 完成视频音频提取、离线转写、文本清洗与改写、实体替换、本地配音，以及 TXT/SRT/WAV/MP3 导出。

开发要求和验收标准见 [CODEX_TASK_PHASE1.md](CODEX_TASK_PHASE1.md)。

## 当前阶段

稳定分支为 `main`，一期开发分支为 `phase1/cpu-mvp`。

## 运行当前 Windows 构建

双击：

```text
E:\pj\video-script-studio\dist\VideoScriptStudio.exe
```

当前首个可执行构建支持项目创建/打开、视频音频提取、原稿编辑、文本清洗、五档离线规则改写、单次确定性替换和 TXT 导出。CPU Whisper 转写、本地 TTS、SRT/MP3 完整工作流仍在后续一期开发中，不应把当前构建视为最终验收版本。

## 从源码运行测试

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q
```

## 重新构建 EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```
