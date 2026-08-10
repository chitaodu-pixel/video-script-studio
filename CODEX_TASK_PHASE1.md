# VideoScript Studio 一期 CPU MVP 开发任务书

> 文档用途：放入 `video-script-studio` GitHub 项目根目录，供 Codex 直接读取并按阶段执行。  
> 目标平台：Windows 10/11，CPU 可运行，离线优先。  
> 本地项目目录：`E:\pj\video-script-studio`。  
> GitHub 仓库：`https://github.com/chitaodu-pixel/video-script-studio`。  
> 开发分支：`phase1/cpu-mvp`。

## 1. 执行指令

Codex 接手后必须先打开 `E:\pj\video-script-studio` 并读取项目根目录中的本文件，检查仓库、分支、远程地址和本机环境，再按第 8 节顺序实施。不得跳过阶段验收，不得擅自扩大一期范围。

唯一预期远程仓库为 `https://github.com/chitaodu-pixel/video-script-studio`。如果 `origin` 缺失，可以添加该地址；如果 `origin` 指向其他地址，必须停止并向用户报告，不得擅自覆盖。

完成定义：主流程可在无云端 API、无 NVIDIA GPU 的 Windows 电脑上跑通；自动化测试通过；Windows 构建成功；文档与实际行为一致；改动已提交到一期分支。

## 2. 一期目标

交付一个可日常试用的 Windows 桌面 MVP，完整跑通：

```text
导入本地视频
  -> FFmpeg 提取 16 kHz 单声道 WAV
  -> faster-whisper 在 CPU 上离线转写
  -> 清洗并展示原稿与时间轴
  -> 规则驱动的离线改写与长度控制
  -> 人名、地点和词语的确定性替换
  -> Windows 本地离线 TTS
  -> 导出 TXT、SRT、MP3/WAV
```

一期必须解决：可恢复的项目流程、后台任务不阻塞界面、进度与错误可见、原始数据不被覆盖、核心逻辑可测试。

## 3. 一期范围

### 3.1 必须实现

- 新建、打开和保存本地项目。
- 导入 `MP4`、`MOV`、`MKV`、`AVI`、`M4V`；保留源文件路径，不把大视频提交 Git。
- 启动时检测 `ffmpeg`、`ffprobe`，缺失时给出可操作提示。
- 提取 WAV：PCM 16-bit、16 kHz、单声道。
- `faster-whisper` CPU 转写，默认 `compute_type=int8`；模型至少支持 `tiny`、`base`、`small`，默认 `small`，允许改为较小模型。
- 保存带 `start`、`end`、`text` 的片段，并生成可编辑原稿。
- 文本清洗：多余空白、重复标点、常见语气词、明显重复片段；必须允许查看未经清洗的转写。
- 离线规则改写：忠实整理、口播优化、精简总结、扩写解说四种模式。
- 长度倍率：`0.5`、`0.75`、`1.0`、`1.5`、`2.0`；显示原文字数、目标字数、实际字数和偏差。
- 实体替换表：原词、替换词、启用状态；按确定性规则处理，较长词优先，禁止级联误替换。
- 本地 TTS：通过 Windows SAPI5（可由 `pyttsx3` 封装）列出已安装声音，支持声音、语速和音量选择；先生成 WAV，必要时用 FFmpeg 转 MP3。
- 导出 UTF-8 TXT、标准 SRT、WAV/MP3；导出前可选原稿、清洗稿或改写稿。
- 所有耗时操作在后台工作线程执行，支持进度、取消和清晰错误提示。
- 日志写入项目日志目录，不记录密钥或无关个人信息。

### 3.2 明确不做

- CUDA/GPU 加速和显存自动管理。
- Ollama、llama.cpp、Qwen 等本地大模型。
- OpenAI、Gemini、DeepSeek、ElevenLabs、Azure 等云端 API。
- 多说话人识别、自动角色分配、声音克隆。
- 视频下载、镜头分析、字幕烧录、自动剪辑和成片输出。
- 自动模型下载器、在线更新器、账号、支付、云同步。
- 为追求“规避原创检测”而进行机械洗稿。

上述内容只能预留接口，不能在一期实现。

## 4. 技术栈与运行基线

| 模块 | 一期选型 | 要求 |
|---|---|---|
| 语言 | Python 3.11 x64 | 类型标注；核心逻辑与 UI 分离 |
| 桌面 UI | PySide6 | Windows 原生桌面应用 |
| 音视频 | FFmpeg / ffprobe | 通过参数数组调用，禁止拼接 shell 字符串 |
| 离线 STT | faster-whisper | CPU + int8；模型目录可配置 |
| 数据模型 | dataclasses 或 Pydantic | 项目文件需要版本字段 |
| 项目存储 | UTF-8 JSON + 项目目录 | 原子写入；一期不强制 SQLite |
| 本地 TTS | SAPI5 / pyttsx3 | 无网络可工作 |
| 测试 | pytest + pytest-qt | 核心逻辑优先单元测试 |
| 质量 | Ruff | lint 与格式检查 |
| 构建 | PyInstaller | 产出 Windows 可执行程序 |

依赖必须固定在 `requirements.txt` 和 `requirements-dev.txt`，或使用等价且清晰的 `pyproject.toml`。不要把 Whisper 模型、媒体文件、虚拟环境或构建产物提交到 Git。

## 5. 建议目录结构

```text
video-script-studio/
├── CODEX_TASK_PHASE1.md
├── README.md
├── AGENTS.md                     # 如存在，优先遵守
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── src/
│   └── video_script_studio/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── domain/
│       │   ├── models.py
│       │   └── errors.py
│       ├── services/
│       │   ├── environment.py
│       │   ├── media.py
│       │   ├── transcription.py
│       │   ├── text_cleaner.py
│       │   ├── rewriter.py
│       │   ├── replacement.py
│       │   ├── tts.py
│       │   ├── exporter.py
│       │   └── project_store.py
│       ├── workers/
│       │   └── task_worker.py
│       └── ui/
│           ├── main_window.py
│           ├── pages/
│           └── widgets/
├── resources/
│   ├── prompts/
│   └── dictionaries/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── check_environment.py
│   └── build_windows.ps1
└── docs/
    ├── USER_GUIDE.md
    └── ARCHITECTURE.md
```

可以因实际代码略调目录，但模块边界和职责不得混在一个大文件中。

## 6. 数据与项目结构

每个用户项目使用独立目录：

```text
projects/<project-id>/
├── project.json
├── media/source-reference.json
├── audio/source.wav
├── transcript/raw_segments.json
├── transcript/original.txt
├── transcript/cleaned.txt
├── rewrite/rewrite.txt
├── rewrite/replacements.json
├── tts/output.wav
├── exports/
└── logs/
```

`project.json` 至少包含：`schema_version`、项目 ID、名称、创建/更新时间、源媒体路径、语言、Whisper 配置、当前文本版本、改写模式、倍率、TTS 配置和各阶段状态。

保存规则：

- 原始转写、清洗稿、改写稿分开保存，后续处理不得覆盖前一版本。
- JSON 先写临时文件再替换，避免中途退出破坏项目。
- 时间统一使用 ISO 8601；文本统一 UTF-8。
- SRT 序号从 1 开始，时间格式为 `HH:MM:SS,mmm`，结束时间不得早于开始时间。

## 7. 核心行为约束

### 7.1 字数控制

中文有效字符统计必须集中在一个函数中，忽略空白；标点是否计数要固定并写入测试。目标值为：

```text
target = round(source_count * ratio)
```

一期规则引擎无法承诺像大模型一样自然地精确扩写。实现要求是：

- `0.5`、`0.75`：按句子重要度、重复度和段落结构压缩，优先保留人物、事实、因果和结论。
- `1.0`：清洗、断句、句式轻量调整，不改变事实。
- `1.5`、`2.0`：只允许基于原文做解释性展开、过渡和摘要回扣；不得生成新人物、数字或事件。
- 默认容差为目标值的 `±10%`；若未达到，最多再校正两轮；仍未达到时保留结果并在 UI 明确显示偏差，不得伪报成功。

### 7.2 替换安全

- 先验证空值、重复键和冲突映射。
- 使用占位符或单次扫描，确保 `A -> B`、`B -> C` 不会把 A 最终变成 C。
- 按原词长度降序匹配，避免短词破坏长词。
- 替换后保留映射表和可撤销的上一个文本版本。

### 7.3 进程与线程

- UI 主线程不得执行 FFmpeg、模型加载、转写、TTS 或大文件 I/O。
- 子进程必须捕获退出码、标准错误并支持超时/取消。
- 用户取消时终止当前任务，保留已完成的稳定产物，清理临时文件。
- 错误信息应说明失败阶段、可能原因和下一步，不向用户展示整段堆栈；完整堆栈写日志。

## 8. 阶段执行顺序

### 阶段 0：接管与基线

1. 打开本地目录 `E:\pj\video-script-studio`，确认它是预期项目根目录。
2. 运行 `git status`、`git branch --show-current`、`git remote -v`。
3. 确认 `origin` 为 `https://github.com/chitaodu-pixel/video-script-studio`（`.git` 后缀有无均可）；缺失时添加，地址冲突时停止并报告。
4. 保留用户已有改动；不得重置或覆盖。
5. 确认或创建 `phase1/cpu-mvp`，禁止直接在 `main` 开发。
6. 检查 Python 3.11、FFmpeg、ffprobe；记录基线结果。
7. 创建最小项目骨架、依赖文件、`.gitignore` 和启动说明。

验收：空应用可启动；环境检查可单独运行；缺失依赖提示明确。

### 阶段 1：项目模型与主界面

实现新建/打开/保存项目、主窗口、步骤导航、状态栏和日志入口。建议页面顺序：导入、转写、文本处理、替换、配音、导出。

验收：重启后可恢复项目；空状态、处理中、成功、失败状态可辨识；保存采用原子写入。

### 阶段 2：媒体导入与音频提取

实现文件选择/拖放、媒体探测、元数据显示、WAV 提取、取消、错误处理和重复运行策略。

验收：至少用一个短视频夹具验证；输出为 PCM 16-bit/16 kHz/mono；路径包含中文和空格时可工作。

### 阶段 3：CPU 离线转写

封装 `TranscriptionService`，后台加载模型并转写，报告进度，保存原始片段 JSON、原稿 TXT 和初始 SRT。

验收：无 GPU、无网络 API 时完成转写；片段按时间排序；空音频、无语音和模型缺失有明确结果。

### 阶段 4：清洗、改写与长度控制

把清洗、句子切分、重要度计算、模式策略、字数统计和校正拆成可测试的纯函数/服务。界面显示三版文本和字数差异。

验收：五种倍率均可运行；事实保护规则生效；结果与目标偏差可见；任何操作都不覆盖原稿。

### 阶段 5：实体替换

实现映射表编辑、导入/导出、启用/禁用、预览和应用；支持撤销到应用前版本。

验收：通过级联、重叠、中文名、空值和重复键测试；映射随项目保存。

### 阶段 6：离线 TTS

列出 SAPI5 声音，支持参数设置和试听；将所选文本分段合成并合并，输出 WAV，可选转换 MP3。

验收：断网可生成音频；无可用声音或 TTS 失败时提示明确；临时分段可清理；最终文件可播放。

### 阶段 7：导出与体验收尾

实现 TXT/SRT/WAV/MP3 导出、覆盖确认、打开输出目录、最近项目、设置持久化和用户指南。

验收：中文不乱码；SRT 时间合法；失败不会留下伪装成成功的空文件。

### 阶段 8：完整测试与 Windows 构建

补齐自动化测试，执行 lint、测试、构建和打包后的烟雾检查；更新 README 和用户指南。

验收：见第 10 节，所有命令通过后才能提交完成状态。

## 9. 测试要求

至少覆盖：

- 字数统计、五档目标计算、容差和最多校正次数。
- 清洗规则的幂等性：同一文本清洗两次结果相同。
- 替换的非级联、长词优先、冲突和空值处理。
- SRT 时间格式、排序、序号和跨小时场景。
- 项目 JSON 往返、版本字段、原子保存和损坏文件错误。
- FFmpeg 参数生成、缺失程序、非零退出码、中文/空格路径。
- 后台工作线程的成功、失败和取消信号。
- TTS 服务在可替换的假实现下测试；自动化测试不得依赖真实系统声音。

集成测试使用短小、可合法提交的合成音频/视频夹具。Whisper 大模型和真实长视频不进入仓库，也不作为普通 CI 的硬性依赖。核心服务应支持依赖注入，以便测试时替换 FFmpeg、STT 和 TTS。

## 10. 质量、测试与构建命令

根据最终依赖管理方式保持命令一致，并写入 README。推荐基线：

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python scripts/check_environment.py
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

构建脚本必须可重复运行，失败返回非零退出码。PyInstaller 产物至少完成：启动、打开空项目、环境检查、关闭应用的烟雾验证。FFmpeg 与 Whisper 模型若未随包分发，首次启动必须明确说明安装/配置方法，不能静默失败。

## 11. Git 流程

1. 开工前确认当前分支为 `phase1/cpu-mvp`，工作区状态已知。
2. 不修改或提交与一期无关的用户文件。
3. 每个阶段完成并通过对应测试后再提交；提交应小而有意义。
4. 推荐提交前缀：`chore:`、`feat:`、`fix:`、`test:`、`docs:`、`build:`。
5. 禁止提交 `.venv/`、模型、源视频/音频、用户项目、日志、缓存、`dist/`、`build/`、密钥或机器专属绝对路径。
6. 最终执行完整 lint、test、build；修复后重新执行，不得只报告已知失败。
7. 推送 `phase1/cpu-mvp` 到 `origin`（`https://github.com/chitaodu-pixel/video-script-studio`）。未经用户明确授权，不合并 `main`、不删除分支、不创建正式 Release。

建议 `.gitignore` 至少包含：

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
build/
dist/
*.spec
models/
projects/
logs/
*.mp4
*.mov
*.mkv
*.avi
*.wav
*.mp3
.env
```

如测试夹具需要媒体文件，应只对 `tests/fixtures/` 做精确例外。

## 12. 最终验收标准

- 在 Windows 10/11、Python 3.11、仅 CPU 的环境中启动并完成主流程。
- 不配置任何云端 API、不使用 NVIDIA GPU 也能完成转写、处理、替换、TTS 和导出。
- 导入一个含中文语音的短视频后，可得到 WAV、片段 JSON、原稿、清洗稿、改写稿、SRT 和可播放音频。
- 五档倍率均可选择；目标、实际和偏差显示正确；超出容差时诚实提示。
- 人名/词语替换不发生级联，支持预览和撤销。
- UI 在所有耗时任务期间保持响应，用户可以取消；失败后仍可继续操作或重试。
- 项目关闭重开后状态与主要设置恢复，原始转写从未被覆盖。
- 中文路径、空格路径和 UTF-8 文本工作正常。
- Ruff、pytest 和 Windows 构建全部通过；打包应用完成烟雾测试。
- README 包含安装、FFmpeg 配置、模型准备、运行、测试、构建、常见错误和隐私说明。
- `git status` 清晰；成果已提交并推送到 `phase1/cpu-mvp`；未擅自合并 `main`。

## 13. Codex 最终回报格式

完成后只报告可验证事实：

1. 已实现的阶段与关键功能。
2. 主要新增/修改文件。
3. 实际执行的 lint、测试、构建命令及结果。
4. 打包产物位置与烟雾测试结果。
5. 未完成项、已知限制和原因。
6. 当前分支、提交哈希和 push 状态。

不得把“计划执行”写成“已完成”，不得隐藏失败，也不得声称一期已经包含第 3.2 节排除的能力。
