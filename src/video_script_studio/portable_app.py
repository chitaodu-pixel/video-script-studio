from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from video_script_studio.domain.models import ReplacementRule
from video_script_studio.services.exporter import export_text
from video_script_studio.services.media import MediaService
from video_script_studio.services.project_store import ProjectStore
from video_script_studio.services.replacement import apply_replacements
from video_script_studio.services.rewriter import rewrite
from video_script_studio.services.text_cleaner import clean_text


class PortableApp(tk.Tk):
    """Dependency-light runnable shell used by the first Windows build."""

    def __init__(self) -> None:
        super().__init__()
        self.title("VideoScript Studio - CPU MVP")
        self.geometry("1050x720")
        self.minsize(850, 600)
        self.store = ProjectStore()
        self.media = MediaService()
        self.project = None
        self.project_root: Path | None = None
        self.status = tk.StringVar(value="准备就绪。请先新建或打开项目。")
        self.ratio = tk.StringVar(value="1.0")
        self.replace_source = tk.StringVar()
        self.replace_target = tk.StringVar()
        self._build()

    def _build(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"))
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="VideoScript Studio", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="新建项目", command=self.create_project).pack(side="right", padx=4)
        ttk.Button(header, text="打开项目", command=self.open_project).pack(side="right", padx=4)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.original = self._text_tab(notebook, "原稿")
        self.cleaned = self._text_tab(notebook, "清洗稿")
        self.rewritten = self._text_tab(notebook, "改写稿")
        tools = ttk.Frame(notebook, padding=16)
        notebook.add(tools, text="处理与导出")

        ttk.Button(tools, text="导入视频并提取 WAV", command=self.import_video).grid(
            row=0, column=0, sticky="ew", pady=5
        )
        ttk.Button(tools, text="清洗原稿", command=self.clean_original).grid(
            row=1, column=0, sticky="ew", pady=5
        )
        ratio_box = ttk.Frame(tools)
        ratio_box.grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Label(ratio_box, text="目标倍率").pack(side="left")
        ttk.Combobox(
            ratio_box,
            textvariable=self.ratio,
            values=("0.5", "0.75", "1.0", "1.5", "2.0"),
            state="readonly",
            width=8,
        ).pack(side="left", padx=8)
        ttk.Button(ratio_box, text="离线规则改写", command=self.rewrite_text).pack(side="left")

        replace = ttk.LabelFrame(tools, text="单次确定性替换", padding=10)
        replace.grid(row=3, column=0, sticky="ew", pady=12)
        ttk.Entry(replace, textvariable=self.replace_source).grid(row=0, column=0, padx=4)
        ttk.Label(replace, text="→").grid(row=0, column=1)
        ttk.Entry(replace, textvariable=self.replace_target).grid(row=0, column=2, padx=4)
        ttk.Button(replace, text="应用", command=self.apply_replacement).grid(row=0, column=3, padx=4)

        ttk.Button(tools, text="导出改写稿 TXT", command=self.export_rewrite).grid(
            row=4, column=0, sticky="ew", pady=5
        )
        tools.columnconfigure(0, weight=1)

        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=6).pack(
            fill="x", padx=12, pady=(0, 10)
        )

    @staticmethod
    def _text_tab(notebook: ttk.Notebook, title: str) -> tk.Text:
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text=title)
        text = tk.Text(frame, wrap="word", font=("Microsoft YaHei UI", 11), undo=True)
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return text

    def _require_project(self) -> bool:
        if self.project and self.project_root:
            return True
        messagebox.showinfo("需要项目", "请先新建或打开项目。", parent=self)
        return False

    def create_project(self) -> None:
        parent = filedialog.askdirectory(title="选择新项目的上级目录", parent=self)
        if not parent:
            return
        root = Path(parent) / "新建视频项目"
        counter = 1
        while root.exists():
            counter += 1
            root = Path(parent) / f"新建视频项目-{counter}"
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
        self._load_text(self.original, root / "transcript" / "original.txt")
        self._load_text(self.cleaned, root / "transcript" / "cleaned.txt")
        self._load_text(self.rewritten, root / "rewrite" / "rewrite.txt")
        self.status.set(f"当前项目：{root}")

    @staticmethod
    def _load_text(widget: tk.Text, path: Path) -> None:
        widget.delete("1.0", "end")
        if path.exists():
            widget.insert("1.0", path.read_text(encoding="utf-8"))

    def import_video(self) -> None:
        if not self._require_project():
            return
        selected = filedialog.askopenfilename(
            title="选择视频",
            filetypes=[("视频", "*.mp4 *.mov *.mkv *.avi *.m4v"), ("所有文件", "*.*")],
            parent=self,
        )
        if not selected:
            return
        source = Path(selected)
        destination = self.project_root / "audio" / "source.wav"
        self.status.set("正在提取音频，请稍候……")

        def work() -> None:
            try:
                self.media.extract_wav(source, destination)
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("音频提取失败", str(exc), parent=self))
                self.after(0, lambda: self.status.set("音频提取失败。"))
                return
            self.project.source_media = str(source)
            self.store.save(self.project_root, self.project)
            self.after(0, lambda: self.status.set(f"音频已生成：{destination}"))

        threading.Thread(target=work, daemon=True).start()

    def clean_original(self) -> None:
        if not self._require_project():
            return
        result = clean_text(self.original.get("1.0", "end-1c"))
        self.cleaned.delete("1.0", "end")
        self.cleaned.insert("1.0", result)
        export_text(self.project_root / "transcript" / "cleaned.txt", result)
        self.status.set("清洗稿已保存。")

    def rewrite_text(self) -> None:
        if not self._require_project():
            return
        source = self.cleaned.get("1.0", "end-1c") or self.original.get("1.0", "end-1c")
        result = rewrite(source, float(self.ratio.get()))
        self.rewritten.delete("1.0", "end")
        self.rewritten.insert("1.0", result.text)
        export_text(self.project_root / "rewrite" / "rewrite.txt", result.text)
        self.status.set(
            f"原文 {result.source_count} 字，目标 {result.target_count} 字，实际 {result.actual_count} 字。"
        )

    def apply_replacement(self) -> None:
        if not self._require_project():
            return
        try:
            output = apply_replacements(
                self.rewritten.get("1.0", "end-1c"),
                [ReplacementRule(self.replace_source.get(), self.replace_target.get())],
            )
        except ValueError as exc:
            messagebox.showwarning("替换规则有误", str(exc), parent=self)
            return
        self.rewritten.delete("1.0", "end")
        self.rewritten.insert("1.0", output)
        export_text(self.project_root / "rewrite" / "rewrite.txt", output)

    def export_rewrite(self) -> None:
        text = self.rewritten.get("1.0", "end-1c")
        destination = filedialog.asksaveasfilename(
            title="导出改写稿", defaultextension=".txt", filetypes=[("文本", "*.txt")], parent=self
        )
        if destination:
            export_text(Path(destination), text)
            self.status.set(f"已导出：{destination}")


def main() -> int:
    app = PortableApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
