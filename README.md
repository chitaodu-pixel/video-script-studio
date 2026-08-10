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

当前可执行构建采用四步工作流：

1. 提取文案：按钮选择或桌面拖入视频，显示进度并把识别结果放入文本框，可保存为 TXT。
2. 洗稿：分别显示原稿和清洗稿，只有点击“洗稿”才处理。
3. 改稿：选择 `0.5`、`0.75`、`1.0`、`1.5` 或 `2.0` 倍，点击“离线规则改写”后生成结果。
4. 文本转语音：可继续编辑文本、选择 Windows 本地声优、生成带时间戳的 MP3 并另存。

提取文案必须使用 `faster-whisper`。程序不会使用 Windows 语音命令识别器冒充视频转写；识别引擎或模型未就绪时会明确停止并报错，不会显示不可信的文案。

## 从源码运行测试

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q
```

## 重新构建 EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```
