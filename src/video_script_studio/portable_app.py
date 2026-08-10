from __future__ import annotations

import queue
import shutil
import sys
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from video_script_studio.services.exporter import export_text
from video_script_studio.services.media import SUPPORTED_VIDEO_EXTENSIONS, MediaService
from video_script_studio.services.project_store import ProjectStore
from video_script_studio.services.rewriter import count_effective_characters, rewrite
from video_script_studio.services.text_cleaner import wash_document
from video_script_studio.services.transcription import TranscriptionService
from video_script_studio.services.windows_tts import WindowsTTSService


class PortableApp(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("VideoScript Studio - 视频文案工作台")
        self.geometry("1100x760")
        self.minsize(900, 650)
        self.store = ProjectStore()
        self.media = MediaService()
        self.transcriber = TranscriptionService()
        self.tts = WindowsTTSService()
        self.project = None
        self.project_root: Path | None = None
        self.selected_video: Path | None = None
        self.generated_audio: Path | None = None
        self.status = tk.StringVar(value="准备就绪。")
        self.ratio = tk.StringVar(value="1.0")
        self.voice = tk.StringVar()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.text_counters: dict[tk.Text, tk.StringVar] = {}
        self._build()
        self.after(100, self._poll_events)
        self.after(300, self._load_voices)

    def _build(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Step.TButton", font=("Microsoft YaHei UI", 11, "bold"), padding=8)
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="VideoScript Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="视频文案提取 · 洗稿 · 改稿 · 配音").pack(side="left", padx=16)
        ttk.Button(header, text="新建项目", command=self.create_project).pack(side="right", padx=4)
        ttk.Button(header, text="打开项目", command=self.open_project).pack(side="right", padx=4)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._build_extract_tab()
        self._build_wash_tab()
        self._build_rewrite_tab()
        self._build_tts_tab()
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=6).pack(
            fill="x", padx=12, pady=(0, 10)
        )

    def _build_extract_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="1  提取文案")
        self.drop_area = ttk.Label(
            tab,
            text="将视频文件拖到这里\n或点击“导入视频文件”\n支持 MP4 / MOV / MKV / AVI / M4V",
            anchor="center",
            relief="groove",
            padding=28,
        )
        self.drop_area.pack(fill="x")
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<DropEnter>>", self._drop_enter)
        self.drop_area.dnd_bind("<<DropLeave>>", self._drop_leave)
        self.drop_area.dnd_bind("<<Drop>>", self._drop_video)
        self.import_button = ttk.Button(tab, text="导入视频文件", command=self.choose_video)
        self.import_button.pack(pady=8)
        self.extract_progress = ttk.Progressbar(tab, maximum=100)
        self.extract_progress.pack(fill="x", pady=(2, 8))
        self.extract_text = self._add_text_box(tab, "提取结果")
        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="保存文案", command=self.save_extract).pack(side="left")
        ttk.Button(
            buttons, text="下一步：复制到洗稿", style="Step.TButton", command=self.to_wash
        ).pack(side="right")

    def _build_wash_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="2  洗稿")
        self.wash_original = self._add_text_box(tab, "原稿", height=9)
        ttk.Button(tab, text="洗稿", style="Step.TButton", command=self.run_wash).pack(pady=7)
        self.wash_result = self._add_text_box(tab, "清洗稿", height=9)
        ttk.Button(
            tab, text="下一步：复制到改稿", style="Step.TButton", command=self.to_rewrite
        ).pack(anchor="e", pady=8)

    def _build_rewrite_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="3  改稿")
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Label(controls, text="目标倍率").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.ratio,
            values=("0.5", "0.75", "1.0", "1.5", "2.0"),
            state="readonly",
            width=8,
        ).pack(side="left", padx=8)
        ttk.Button(controls, text="离线规则改写", command=self.run_rewrite).pack(side="left")
        self.rewrite_count = ttk.Label(controls, text="原文 0 / 目标 0 / 实际 0")
        self.rewrite_count.pack(side="left", padx=14)
        self.rewrite_source = self._add_text_box(tab, "待改稿", height=8)
        self.rewrite_result = self._add_text_box(tab, "改写结果", height=11)
        ttk.Button(
            tab, text="下一步：复制到文本转语音", style="Step.TButton", command=self.to_tts
        ).pack(anchor="e", pady=8)

    def _build_tts_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(tab, text="4  文本转语音")
        self.tts_text = self._add_text_box(tab, "配音文本（可继续编辑）", height=15)
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=8)
        ttk.Label(controls, text="声优").pack(side="left")
        self.voice_combo = ttk.Combobox(controls, textvariable=self.voice, state="readonly", width=38)
        self.voice_combo.pack(side="left", padx=8)
        ttk.Button(controls, text="刷新声优", command=self._load_voices).pack(side="left")
        ttk.Button(controls, text="转语音", style="Step.TButton", command=self.run_tts).pack(side="right")
        self.tts_progress = ttk.Progressbar(tab, maximum=100)
        self.tts_progress.pack(fill="x", pady=8)
        self.audio_label = ttk.Label(tab, text="尚未生成 MP3")
        self.audio_label.pack(anchor="w")
        ttk.Button(tab, text="保存 MP3", command=self.save_audio).pack(anchor="e", pady=8)

    def _add_text_box(self, parent, label: str, height: int = 12) -> tk.Text:
        heading = ttk.Frame(parent)
        heading.pack(fill="x", pady=(5, 2))
        ttk.Label(heading, text=label).pack(side="left")
        counter = tk.StringVar(value="字数：0")
        ttk.Label(heading, textvariable=counter).pack(side="right")
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", height=height, font=("Microsoft YaHei UI", 11), undo=True)
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.text_counters[text] = counter
        text.bind("<<Modified>>", self._on_text_modified, add="+")
        text.edit_modified(False)
        return text

    def _on_text_modified(self, event) -> None:
        widget = event.widget
        if widget.edit_modified():
            self._update_text_counter(widget)
            widget.edit_modified(False)

    def _update_text_counter(self, widget: tk.Text) -> None:
        counter = self.text_counters.get(widget)
        if counter is not None:
            text = widget.get("1.0", "end-1c")
            counter.set(f"字数：{count_effective_characters(text)}")

    def _drop_enter(self, event):
        self.drop_area.configure(text="松开鼠标即可导入视频")
        return event.action

    def _drop_leave(self, event):
        if not self.selected_video:
            self.drop_area.configure(text="将视频文件拖到这里\n支持 MP4 / MOV / MKV / AVI / M4V")
        return event.action

    def _drop_video(self, event):
        paths = [Path(item) for item in self.tk.splitlist(event.data)]
        if paths:
            self.start_extraction(paths[0])
        return event.action

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "audio_ready":
                    self.status.set("正在加载本地 Whisper 模型，请稍候……")
                elif kind == "progress":
                    if str(self.extract_progress["mode"]) != "determinate":
                        self.extract_progress.stop()
                        self.extract_progress.configure(mode="determinate")
                    self.extract_progress.configure(value=20 + int(payload) * 0.8)
                    self.status.set(f"正在使用 CPU 识别视频文案…… {int(payload)}%")
                elif kind == "extract_done":
                    self._extraction_finished(str(payload))
                elif kind == "extract_error":
                    self._extraction_failed(str(payload))
                elif kind == "tts_done":
                    self._tts_finished(Path(str(payload)))
                elif kind == "tts_error":
                    self._tts_failed(str(payload))
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _ensure_project(self) -> bool:
        if self.project and self.project_root:
            return True
        base = Path.home() / "Documents" / "VideoScriptStudioProjects"
        base.mkdir(parents=True, exist_ok=True)
        root = base / datetime.now().strftime("项目-%Y%m%d-%H%M%S")
        try:
            self.project = self.store.create(root, root.name)
        except OSError as exc:
            messagebox.showerror("无法创建项目", str(exc), parent=self)
            return False
        self.project_root = root
        self.status.set(f"已自动创建项目：{root}")
        return True

    def create_project(self) -> None:
        parent = filedialog.askdirectory(title="选择新项目的上级目录", parent=self)
        if not parent:
            return
        root = Path(parent) / datetime.now().strftime("视频项目-%Y%m%d-%H%M%S")
        try:
            self.project = self.store.create(root, root.name)
        except OSError as exc:
            messagebox.showerror("无法新建项目", str(exc), parent=self)
            return
        self.project_root = root
        self.status.set(f"当前项目：{root}")

    def open_project(self) -> None:
        selected = filedialog.askdirectory(title="选择项目目录", parent=self)
        if not selected:
            return
        root = Path(selected)
        try:
            self.project = self.store.load(root)
        except Exception as exc:
            messagebox.showerror("无法打开项目", str(exc), parent=self)
            return
        self.project_root = root
        self._load_widget(self.extract_text, root / "transcript" / "original.txt")
        self._load_widget(self.wash_original, root / "transcript" / "original.txt")
        self._load_widget(self.wash_result, root / "transcript" / "cleaned.txt")
        self._load_widget(self.rewrite_result, root / "rewrite" / "rewrite.txt")
        self.status.set(f"当前项目：{root}")

    def _load_widget(self, widget: tk.Text, path: Path) -> None:
        widget.delete("1.0", "end")
        if path.exists():
            widget.insert("1.0", path.read_text(encoding="utf-8"))
        self._update_text_counter(widget)

    def _set_widget(self, widget: tk.Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        self._update_text_counter(widget)

    def choose_video(self) -> None:
        selected = filedialog.askopenfilename(
            title="导入视频文件",
            filetypes=[("视频文件", "*.mp4 *.mov *.mkv *.avi *.m4v"), ("所有文件", "*.*")],
            parent=self,
        )
        if selected:
            self.start_extraction(Path(selected))

    def start_extraction(self, source: Path) -> None:
        if source.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            messagebox.showwarning("不支持的文件", f"不支持 {source.suffix} 格式。", parent=self)
            return
        if not source.is_file():
            messagebox.showerror("文件不存在", str(source), parent=self)
            return
        if not self._ensure_project():
            return
        self.selected_video = source
        self.import_button.configure(state="disabled")
        self.drop_area.configure(text=f"已导入：{source.name}\n正在提取文案……")
        self.extract_progress.configure(mode="indeterminate", value=0)
        self.extract_progress.start(12)
        self.status.set("正在从视频提取音频……")
        audio = self.project_root / "audio" / "source.wav"

        def work() -> None:
            try:
                self.media.extract_wav(source, audio)
                self.events.put(("audio_ready", None))
                segments = self.transcriber.transcribe(
                    audio, "small", "zh", lambda value: self.events.put(("progress", value))
                )
                self.transcriber.save_segments(
                    self.project_root / "transcript" / "raw_segments.json", segments
                )
                text = "".join(segment.text for segment in segments)
                export_text(self.project_root / "transcript" / "original.txt", text)
                self.project.source_media = str(source)
                self.project.stage_status["transcription"] = "completed"
                self.store.save(self.project_root, self.project)
            except Exception as exc:
                self._write_error_log(exc)
                self.events.put(("extract_error", f"{type(exc).__name__}: {exc}"))
                return
            self.events.put(("extract_done", text))

        threading.Thread(target=work, daemon=True, name="video-transcription").start()

    def _write_error_log(self, exc: Exception) -> None:
        root = self.project_root or Path.home() / "Documents" / "VideoScriptStudioProjects"
        path = root / "logs" / "app.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] {type(exc).__name__}: {exc}\n")
            handle.write(traceback.format_exc())

    def _extraction_failed(self, message: str) -> None:
        self.extract_progress.stop()
        self.extract_progress.configure(mode="determinate", value=0)
        self.import_button.configure(state="normal")
        self.status.set("文案提取失败。")
        messagebox.showerror(
            "文案提取失败",
            f"{message}\n\n错误详情已保存到当前项目的 logs\\app.log。",
            parent=self,
        )

    def _extraction_finished(self, text: str) -> None:
        self.extract_progress.stop()
        self.extract_progress.configure(mode="determinate", value=100)
        self.import_button.configure(state="normal")
        self._set_widget(self.extract_text, text)
        self.drop_area.configure(text=f"已完成：{self.selected_video.name}")
        self.status.set(f"文案提取完成，共 {count_effective_characters(text)} 字。")

    def save_extract(self) -> None:
        destination = filedialog.asksaveasfilename(
            title="保存提取文案", defaultextension=".txt", filetypes=[("文本", "*.txt")], parent=self
        )
        if destination:
            export_text(Path(destination), self.extract_text.get("1.0", "end-1c"))
            self.status.set(f"提取文案已保存：{destination}")

    def to_wash(self) -> None:
        self._set_widget(self.wash_original, self.extract_text.get("1.0", "end-1c"))
        self.notebook.select(1)

    def run_wash(self) -> None:
        source = self.wash_original.get("1.0", "end-1c")
        wash = wash_document(source)
        result = wash.text
        self._set_widget(self.wash_result, result)
        if self._ensure_project():
            export_text(self.project_root / "transcript" / "cleaned.txt", result)
        similarity = round(wash.similarity * 100)
        self.status.set(
            f"洗稿完成：校正 {wash.correction_count} 处，改写 {wash.rewrite_count} 处，"
            f"文字相似度约 {similarity}%；请人工复核专有名词。"
        )

    def to_rewrite(self) -> None:
        self._set_widget(self.rewrite_source, self.wash_result.get("1.0", "end-1c"))
        self.notebook.select(2)

    def run_rewrite(self) -> None:
        result = rewrite(self.rewrite_source.get("1.0", "end-1c"), float(self.ratio.get()))
        self._set_widget(self.rewrite_result, result.text)
        self.rewrite_count.configure(
            text=f"原文 {result.source_count} / 目标 {result.target_count} / 实际 {result.actual_count}"
        )
        if self._ensure_project():
            export_text(self.project_root / "rewrite" / "rewrite.txt", result.text)
        self.status.set("改稿完成。" if result.within_tolerance else "改稿完成，但字数超出目标容差。")

    def to_tts(self) -> None:
        self._set_widget(self.tts_text, self.rewrite_result.get("1.0", "end-1c"))
        self.notebook.select(3)

    def _load_voices(self) -> None:
        try:
            voices = self.tts.voices()
        except Exception as exc:
            self.status.set(f"无法读取 Windows 声优：{exc}")
            return
        self.voice_combo.configure(values=voices)
        if voices and not self.voice.get():
            self.voice.set(voices[0])

    def run_tts(self) -> None:
        if not self._ensure_project():
            return
        text = self.tts_text.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("没有文本", "请先填写配音文本。", parent=self)
            return
        destination = self.project_root / "tts" / f"配音-{datetime.now():%Y%m%d-%H%M%S}.mp3"
        self.tts_progress.configure(value=10)
        self.status.set("正在转换语音……")

        def work() -> None:
            try:
                self.tts.synthesize_mp3(text, destination, self.voice.get())
            except Exception as exc:
                self._write_error_log(exc)
                self.events.put(("tts_error", f"{type(exc).__name__}: {exc}"))
                return
            self.events.put(("tts_done", str(destination)))

        threading.Thread(target=work, daemon=True, name="text-to-speech").start()

    def _tts_failed(self, message: str) -> None:
        self.tts_progress.configure(value=0)
        self.status.set("文本转语音失败。")
        messagebox.showerror("文本转语音失败", message, parent=self)

    def _tts_finished(self, destination: Path) -> None:
        self.generated_audio = destination
        self.tts_progress.configure(value=100)
        self.audio_label.configure(text=f"已生成：{destination.name}")
        self.status.set(f"MP3 已生成：{destination}")

    def save_audio(self) -> None:
        if not self.generated_audio or not self.generated_audio.exists():
            messagebox.showinfo("没有音频", "请先完成文本转语音。", parent=self)
            return
        destination = filedialog.asksaveasfilename(
            title="保存 MP3",
            defaultextension=".mp3",
            initialfile=self.generated_audio.name,
            filetypes=[("MP3 音频", "*.mp3")],
            parent=self,
        )
        if destination:
            shutil.copy2(self.generated_audio, destination)
            self.status.set(f"MP3 已保存：{destination}")


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--self-test":
        source = Path(sys.argv[2])
        output = Path(sys.argv[3])
        audio = output.with_suffix(".wav")
        try:
            MediaService().extract_wav(source, audio)
            segments = TranscriptionService().transcribe(audio, "small", "zh")
            export_text(output, "".join(segment.text for segment in segments))
        except Exception:
            output.with_suffix(".error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            return 1
        finally:
            audio.unlink(missing_ok=True)
        return 0
    app = PortableApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
