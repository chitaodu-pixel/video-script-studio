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
4. **文本转语音**：编辑文本、选择离线或在线声优，生成带时间戳文件名的试听 MP3，可试听、另存或一键清除全部试听文件。

## 配音引擎

程序支持三种配音引擎：

- **离线神经中文**：内置两位女声和两位男声，无需联网或密钥，默认使用此引擎。
- **Windows 本地**：无需联网或密钥，使用电脑已安装的声优。
- **Azure 在线神经**：填写 Azure Speech 资源的密钥和区域后，点击“刷新声优”读取中文神经声优。勾选“记住密钥”后，密钥由 Windows 当前用户加密保存，不写入项目或 EXE。

三种引擎都可以调节语速、音调和音量。在线合成会将配音文本发送到所选 Azure Speech 区域，请根据内容隐私要求选择是否使用。

离线神经中文模型必须保存在：

```text
E:\pj\video-script-studio\models\kokoro-v1.1-zh
```

其中包含 `kokoro-v1.1-zh.onnx`、`voices-v1.1-zh.bin` 和 `config.json`。

转语音生成的临时试听统一保存在当前项目的 `tts\previews` 文件夹。点击“保存 MP3”另存的文件不会被“清除全部试听”删除。

未手动选择项目时，软件会在 EXE 所在目录的 `projects` 文件夹创建项目。例如 EXE 位于 `E:\pj\video-script-studio\dist`，自动项目将保存在 `E:\pj\video-script-studio\dist\projects`，不会再默认写入C盘“文档”目录。

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
