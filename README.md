# VideoScript Studio

Windows 本地视频文案处理工具。一期 CPU MVP 提供四步工作流：提取文案、洗稿、改稿和文本转语音。

- 项目目录：`E:\pj\video-script-studio`
- GitHub：<https://github.com/chitaodu-pixel/video-script-studio>
- 开发任务书：[CODEX_TASK_PHASE1.md](CODEX_TASK_PHASE1.md)
- 开发分支：`phase1/cpu-mvp`

## 运行 Windows 版本

双击：

```text
E:\pj\video-script-studio\dist\VideoScriptStudio.exe
```

## 四步功能

1. **提取文案**：选择或从桌面拖入视频，显示处理进度，并将识别结果放入文本框，可保存为 TXT。
2. **洗稿**：上方显示原稿，下方显示清洗稿；只有点击“洗稿”才开始处理。
3. **改稿**：选择目标倍率，点击“离线规则改写”后生成结果。
4. **文本转语音**：编辑文本、选择 Windows 本地声优，生成带时间戳文件名的 MP3 并另存。

## 离线语音识别模型

提取文案使用 `faster-whisper`，不会使用不适合视频转写的 Windows 语音命令识别器。

模型必须保存在：

```text
E:\pj\video-script-studio\models\faster-whisper-small
```

该目录至少应包含：

```text
config.json
model.bin
tokenizer.json
vocabulary.txt
```

模型文件不提交到 Git。运行 EXE 时请保留项目中的 `models` 目录及以上文件。

## 运行测试

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q
```

## 重新构建 EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```
