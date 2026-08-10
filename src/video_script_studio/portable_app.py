from __future__ import annotations

import ctypes
import threading
import tkinter as tk
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from video_script_studio.services.exporter import export_text
from video_script_studio.services.media import SUPPORTED_VIDEO_EXTENSIONS, MediaService
from video_script_studio.services.project_store import ProjectStore
from video_script_studio.services.rewriter import count_effective_characters, rewrite
from video_script_studio.services.text_cleaner import clean_text
from video_script_studio.services.transcription import TranscriptionService
from video_script_studio.services.windows_tts import WindowsTTSService

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4


class PortableApp(tk.Tk):
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
        self.status = tk.StringVar(value="准备就绪。")
        self.ratio = tk.StringVar(value="1.0")
        self.voice = tk.StringVar()
        self._drop_callback = None
        self._original_wndproc = None
        self._build()
        self.after(250, self._enable_windows_drop)
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
            text="将视频拖到这里\n或点击“导入视频文件”\n支持 MP4 / MOV / MKV / AVI / M4V",
            anchor="center",
            relief="groove",
            padding=28,
        )
        self.drop_area.pack(fill="x")
        ttk.Button(tab, text="导入视频文件", command=self.choose_video).pack(pady=8)
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
        ttk.Button(controls, text="转语音", style="Step.TButton", command=self.run_tts).pack(
            side="right"
        )
        self.tts_progress = ttk.Progressbar(tab, maximum=100)
        self.tts_progress.pack(fill="x", pady=8)
        self.generated_audio: Path | None = None
        self.audio_label = ttk.Label(tab, text="尚未生成 MP3")
        self.audio_label.pack(anchor="w")
        ttk.Button(tab, text="保存 MP3", command=self.save_audio).pack(anchor="e", pady=8)

    @staticmethod
    def _add_text_box(parent, label: str, height: int = 12) -> tk.Text:
        ttk.Label(parent, text=label).pack(anchor="w", pady=(5, 2))
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", height=height, font=("Microsoft YaHei UI", 11), undo=True)
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return text

    def _enable_windows_drop(self) -> None:
        if not hasattr(ctypes, "windll"):
            return
        hwnd = self.winfo_id()
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        shell32.DragAcceptFiles(hwnd, True)
        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = ctypes.c_void_p
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = ctypes.c_longlong
        original = user32.GetWindowLongPtrW(hwnd, GWLP_WNDPROC)
        self._original_wndproc = original

        @callback_type
        def wndproc(window, message, wparam, lparam):
            if message == WM_DROPFILES:
                length = shell32.DragQueryFileW(wparam, 0, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(wparam, 0, buffer, length + 1)
                shell32.DragFinish(wparam)
                self.after(0, lambda path=buffer.value: self.start_extraction(Path(path)))
                return 0
            return user32.CallWindowProcW(original, window, message, wparam, lparam)

        self._drop_callback = wndproc
        user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, ctypes.cast(wndproc, ctypes.c_void_p))

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

    @staticmethod
    def _load_widget(widget: tk.Text, path: Path) -> None:
        widget.delete("1.0", "end")
        if path.exists():
            widget.insert("1.0", path.read_text(encoding="utf-8"))

    @staticmethod
    def _set_widget(widget: tk.Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

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
        if not self._ensure_project():
            return
        self.selected_video = source
        self.drop_area.configure(text=f"已导入：{source.name}\n正在提取文案……")
        self.extract_progress.configure(value=2)
        self.status.set("正在从视频提取音频……")
        audio = self.project_root / "audio" / "source.wav"

        def work() -> None:
            try:
                self.media.extract_wav(source, audio)
                self.after(0, lambda: self.extract_progress.configure(value=20))
                self.after(0, lambda: self.status.set("正在使用 CPU 识别视频文案……"))

                def progress(value: int) -> None:
                    self.after(0, lambda v=value: self.extract_progress.configure(value=20 + v * 0.8))

                segments = self.transcriber.transcribe(audio, "small", "zh", progress)
                self.transcriber.save_segments(
                    self.project_root / "transcript" / "raw_segments.json", segments
                )
                text = "".join(segment.text for segment in segments)
                export_text(self.project_root / "transcript" / "original.txt", text)
                self.project.source_media = str(source)
                self.project.stage_status["transcription"] = "completed"
                self.store.save(self.project_root, self.project)
            except Exception as exc:
                self.after(0, lambda: self._extraction_failed(str(exc)))
                return
            self.after(0, lambda: self._extraction_finished(text))

        threading.Thread(target=work, daemon=True).start()

    def _extraction_failed(self, message: str) -> None:
        self.extract_progress.configure(value=0)
        self.status.set("文案提取失败。")
        messagebox.showerror(
            "文案提取失败",
            f"{message}\n\n程序不会再使用低质量的 Windows 语音识别结果代替 Whisper。",
            parent=self,
        )

    def _extraction_finished(self, text: str) -> None:
        self.extract_progress.configure(value=100)
        self._set_widget(self.extract_text, text)
        self.drop_area.configure(text=f"已完成：{self.selected_video.name}")
        self.status.set(f"文案提取完成，共 {count_effective_characters(text)} 字。")

    def save_extract(self) -> None:
        text = self.extract_text.get("1.0", "end-1c")
        destination = filedialog.asksaveasfilename(
            title="保存提取文案", defaultextension=".txt", filetypes=[("文本", "*.txt")], parent=self
        )
        if destination:
            export_text(Path(destination), text)
            self.status.set(f"提取文案已保存：{destination}")

    def to_wash(self) -> None:
        self._set_widget(self.wash_original, self.extract_text.get("1.0", "end-1c"))
        self.notebook.select(1)

    def run_wash(self) -> None:
        source = self.wash_original.get("1.0", "end-1c")
        result = clean_text(source)
        self._set_widget(self.wash_result, result)
        if self._ensure_project():
            export_text(self.project_root / "transcript" / "cleaned.txt", result)
        self.status.set("洗稿完成；原稿未被覆盖。")

    def to_rewrite(self) -> None:
        self._set_widget(self.rewrite_source, self.wash_result.get("1.0", "end-1c"))
        self.notebook.select(2)

    def run_rewrite(self) -> None:
        source = self.rewrite_source.get("1.0", "end-1c")
        result = rewrite(source, float(self.ratio.get()))
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
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = self.project_root / "tts" / f"配音-{timestamp}.mp3"
        self.tts_progress.configure(value=5)
        self.status.set("正在转换语音……")

        def work() -> None:
            try:
                self.after(0, lambda: self.tts_progress.configure(value=20))
                self.tts.synthesize_mp3(text, destination, self.voice.get())
            except Exception as exc:
                self.after(0, lambda: self._tts_failed(str(exc)))
                return
            self.after(0, lambda: self._tts_finished(destination))

        threading.Thread(target=work, daemon=True).start()

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
            Path(destination).write_bytes(self.generated_audio.read_bytes())
            self.status.set(f"MP3 已保存：{destination}")


def main() -> int:
    app = PortableApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
