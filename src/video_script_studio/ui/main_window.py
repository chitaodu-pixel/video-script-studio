from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video_script_studio.domain.models import Project, ReplacementRule
from video_script_studio.services.environment import check_environment
from video_script_studio.services.exporter import export_text, render_srt
from video_script_studio.services.media import MediaService
from video_script_studio.services.project_store import ProjectStore
from video_script_studio.services.replacement import apply_replacements
from video_script_studio.services.rewriter import count_effective_characters, rewrite
from video_script_studio.services.text_cleaner import clean_text
from video_script_studio.services.transcription import TranscriptionService
from video_script_studio.services.tts import LocalTTSService
from video_script_studio.workers.task_worker import TaskWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VideoScript Studio - CPU MVP")
        self.resize(1120, 760)
        self.store = ProjectStore()
        self.media_service = MediaService()
        self.project: Project | None = None
        self.project_root: Path | None = None
        self.thread_pool = QThreadPool.globalInstance()
        self.current_worker: TaskWorker | None = None
        self.pages = QStackedWidget()
        self.log_view = QTextEdit(readOnly=True)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self._build_ui()
        self._check_environment()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        title = QLabel("VideoScript Studio")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        for label, handler in (("新建项目", self.create_project), ("打开项目", self.open_project)):
            button = QPushButton(label)
            button.clicked.connect(handler)
            header.addWidget(button)
        layout.addLayout(header)

        navigation = QHBoxLayout()
        page_builders = (
            ("导入", self._build_import_page),
            ("转写", self._build_transcribe_page),
            ("文本处理", self._build_rewrite_page),
            ("替换", self._build_replacement_page),
            ("配音", self._build_tts_page),
            ("导出", self._build_export_page),
        )
        for index, (label, builder) in enumerate(page_builders):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, i=index: self.pages.setCurrentIndex(i))
            navigation.addWidget(button)
            self.pages.addWidget(builder())
        layout.addLayout(navigation)
        layout.addWidget(self.pages, 1)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("运行日志"))
        self.log_view.setMaximumHeight(125)
        layout.addWidget(self.log_view)
        self.setCentralWidget(root)
        self.statusBar().showMessage("准备就绪")

    def _build_import_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.source_label = QLabel("尚未选择视频")
        button = QPushButton("选择本地视频并提取音频")
        button.clicked.connect(self.import_video)
        layout.addWidget(self.source_label)
        layout.addWidget(button)
        layout.addStretch()
        return page

    def _build_transcribe_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small"])
        self.model_combo.setCurrentText("small")
        transcribe_button = QPushButton("开始 CPU 离线转写")
        transcribe_button.clicked.connect(self.transcribe_audio)
        controls.addWidget(QLabel("Whisper 模型"))
        controls.addWidget(self.model_combo)
        controls.addWidget(transcribe_button)
        controls.addStretch()
        self.original_editor = QTextEdit()
        self.original_editor.setPlaceholderText("转写原稿将在这里显示，也可以手动编辑。")
        layout.addLayout(controls)
        layout.addWidget(self.original_editor)
        return page

    def _build_rewrite_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        clean_button = QPushButton("清洗原稿")
        clean_button.clicked.connect(self.clean_original)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["0.5", "0.75", "1.0", "1.5", "2.0"])
        rewrite_button = QPushButton("离线规则改写")
        rewrite_button.clicked.connect(self.rewrite_text)
        self.count_label = QLabel("原文 0 / 目标 0 / 实际 0")
        controls.addWidget(clean_button)
        controls.addWidget(QLabel("目标倍率"))
        controls.addWidget(self.ratio_combo)
        controls.addWidget(rewrite_button)
        controls.addWidget(self.count_label)
        controls.addStretch()
        self.cleaned_editor = QTextEdit()
        self.cleaned_editor.setPlaceholderText("清洗稿")
        self.rewrite_editor = QTextEdit()
        self.rewrite_editor.setPlaceholderText("改写稿")
        layout.addLayout(controls)
        layout.addWidget(QLabel("清洗稿"))
        layout.addWidget(self.cleaned_editor)
        layout.addWidget(QLabel("改写稿"))
        layout.addWidget(self.rewrite_editor)
        return page

    def _build_replacement_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.replacement_table = QTableWidget(0, 2)
        self.replacement_table.setHorizontalHeaderLabels(["原词", "替换词"])
        controls = QHBoxLayout()
        add_button = QPushButton("添加规则")
        add_button.clicked.connect(self.add_replacement_row)
        apply_button = QPushButton("预览并应用到改写稿")
        apply_button.clicked.connect(self.apply_replacement_rules)
        controls.addWidget(add_button)
        controls.addWidget(apply_button)
        controls.addStretch()
        layout.addWidget(self.replacement_table)
        layout.addLayout(controls)
        return page

    def _build_tts_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        self.voice_combo = QComboBox()
        load_button = QPushButton("加载 Windows 本地声音")
        load_button.clicked.connect(self.load_voices)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(80, 350)
        self.rate_spin.setValue(180)
        synthesize_button = QPushButton("生成 WAV")
        synthesize_button.clicked.connect(self.synthesize_audio)
        layout.addRow(load_button, self.voice_combo)
        layout.addRow("语速", self.rate_spin)
        layout.addRow(synthesize_button)
        return page

    def _build_export_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.export_version = QComboBox()
        self.export_version.addItems(["原稿", "清洗稿", "改写稿"])
        button = QPushButton("导出 UTF-8 TXT")
        button.clicked.connect(self.export_txt)
        srt_button = QPushButton("导出 SRT")
        srt_button.clicked.connect(self.export_srt)
        audio_button = QPushButton("导出 WAV / MP3")
        audio_button.clicked.connect(self.export_audio)
        layout.addWidget(self.export_version)
        layout.addWidget(button)
        layout.addWidget(srt_button)
        layout.addWidget(audio_button)
        layout.addStretch()
        return page

    def _require_project(self) -> bool:
        if self.project and self.project_root:
            return True
        QMessageBox.information(self, "需要项目", "请先新建或打开一个项目。")
        return False

    def _check_environment(self) -> None:
        for item in check_environment():
            detail = item.version or item.guidance or ""
            self.log(f"{item.name}: {'正常' if item.available else '需要处理'} - {detail}")

    def log(self, message: str) -> None:
        self.log_view.append(message)

    def create_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择新项目的上级目录")
        if not selected:
            return
        root = Path(selected) / "新建视频项目"
        suffix = 1
        while root.exists():
            suffix += 1
            root = Path(selected) / f"新建视频项目-{suffix}"
        try:
            self.project = self.store.create(root, root.name)
        except OSError as exc:
            QMessageBox.critical(self, "无法新建项目", str(exc))
            return
        self.project_root = root
        self.statusBar().showMessage(f"当前项目：{root}")
        self.log(f"已创建项目：{root}")

    def open_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if not selected:
            return
        root = Path(selected)
        try:
            self.project = self.store.load(root)
        except Exception as exc:
            QMessageBox.critical(self, "无法打开项目", str(exc))
            return
        self.project_root = root
        self._load_project_texts()
        self.statusBar().showMessage(f"当前项目：{root}")
        self.log(f"已打开项目：{self.project.name}")

    def _load_project_texts(self) -> None:
        assert self.project_root
        for editor, relative in (
            (self.original_editor, "transcript/original.txt"),
            (self.cleaned_editor, "transcript/cleaned.txt"),
            (self.rewrite_editor, "rewrite/rewrite.txt"),
        ):
            path = self.project_root / relative
            if path.exists():
                editor.setPlainText(path.read_text(encoding="utf-8"))

    def _run_task(self, task, on_success) -> None:
        self.progress.setValue(0)
        self.progress.setVisible(True)
        worker = TaskWorker(task)
        self.current_worker = worker
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.finished.connect(lambda result: self._task_finished(result, on_success))
        worker.signals.failed.connect(self._task_failed)
        self.thread_pool.start(worker)

    def _task_finished(self, result, callback) -> None:
        self.progress.setVisible(False)
        self.current_worker = None
        callback(result)

    def _task_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.current_worker = None
        self.log(f"任务失败：{message}")
        QMessageBox.critical(self, "任务失败", message)

    def import_video(self) -> None:
        if not self._require_project():
            return
        source_name, _ = QFileDialog.getOpenFileName(
            self, "选择视频", "", "视频 (*.mp4 *.mov *.mkv *.avi *.m4v)"
        )
        if not source_name:
            return
        source = Path(source_name)
        destination = self.project_root / "audio" / "source.wav"

        def task(progress):
            progress(5)
            info = self.media_service.probe(source)
            progress(15)
            self.media_service.extract_wav(source, destination)
            progress(100)
            return info

        def success(info):
            self.project.source_media = str(source)
            self.project.stage_status["media"] = "completed"
            self.store.save(self.project_root, self.project)
            self.source_label.setText(f"{source}\n时长：{info.duration:.1f} 秒")
            self.log(f"音频已提取：{destination}")

        self._run_task(task, success)

    def transcribe_audio(self) -> None:
        if not self._require_project():
            return
        audio = self.project_root / "audio" / "source.wav"
        if not audio.exists():
            QMessageBox.information(self, "缺少音频", "请先导入视频并提取音频。")
            return
        model = self.model_combo.currentText()

        def task(progress):
            return TranscriptionService().transcribe(audio, model, self.project.language, progress)

        def success(segments):
            service = TranscriptionService()
            service.save_segments(self.project_root / "transcript" / "raw_segments.json", segments)
            text = "".join(segment.text for segment in segments)
            export_text(self.project_root / "transcript" / "original.txt", text)
            export_text(self.project_root / "transcript" / "subtitle.srt", render_srt(segments))
            self.original_editor.setPlainText(text)
            self.project.whisper_model = model
            self.project.stage_status["transcription"] = "completed"
            self.store.save(self.project_root, self.project)
            self.log(f"转写完成，共 {len(segments)} 个片段。")

        self._run_task(task, success)

    def clean_original(self) -> None:
        text = clean_text(self.original_editor.toPlainText())
        self.cleaned_editor.setPlainText(text)
        if self._require_project():
            export_text(self.project_root / "transcript" / "cleaned.txt", text)

    def rewrite_text(self) -> None:
        if not self._require_project():
            return
        source = self.cleaned_editor.toPlainText() or self.original_editor.toPlainText()
        result = rewrite(source, float(self.ratio_combo.currentText()))
        self.rewrite_editor.setPlainText(result.text)
        self.count_label.setText(
            f"原文 {result.source_count} / 目标 {result.target_count} / 实际 {result.actual_count}"
        )
        export_text(self.project_root / "rewrite" / "rewrite.txt", result.text)
        self.project.rewrite_ratio = float(self.ratio_combo.currentText())
        self.project.stage_status["rewrite"] = "completed"
        self.store.save(self.project_root, self.project)
        if not result.within_tolerance:
            self.log("改写结果超出目标容差，实际偏差已在界面显示。")

    def add_replacement_row(self) -> None:
        row = self.replacement_table.rowCount()
        self.replacement_table.insertRow(row)
        self.replacement_table.setItem(row, 0, QTableWidgetItem(""))
        self.replacement_table.setItem(row, 1, QTableWidgetItem(""))

    def apply_replacement_rules(self) -> None:
        if not self._require_project():
            return
        rules = []
        for row in range(self.replacement_table.rowCount()):
            source = self.replacement_table.item(row, 0)
            target = self.replacement_table.item(row, 1)
            rules.append(ReplacementRule(source.text() if source else "", target.text() if target else ""))
        try:
            text = apply_replacements(self.rewrite_editor.toPlainText(), rules)
        except ValueError as exc:
            QMessageBox.warning(self, "替换规则有误", str(exc))
            return
        self.rewrite_editor.setPlainText(text)
        export_text(self.project_root / "rewrite" / "rewrite.txt", text)
        mapping = [asdict(rule) for rule in rules]
        (self.project_root / "rewrite" / "replacements.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_voices(self) -> None:
        try:
            voices = LocalTTSService().voices()
        except Exception as exc:
            QMessageBox.critical(self, "无法加载声音", str(exc))
            return
        self.voice_combo.clear()
        for voice in voices:
            self.voice_combo.addItem(voice.name, voice.voice_id)

    def synthesize_audio(self) -> None:
        if not self._require_project():
            return
        text = self.rewrite_editor.toPlainText() or self.cleaned_editor.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "没有文本", "请先准备需要配音的文本。")
            return
        destination = self.project_root / "tts" / "output.wav"
        voice_id = self.voice_combo.currentData()
        rate = self.rate_spin.value()

        def task(progress):
            progress(5)
            LocalTTSService().synthesize(text, destination, voice_id, rate, 1.0)
            progress(100)
            return destination

        self._run_task(task, lambda path: self.log(f"配音已生成：{path}"))

    def export_txt(self) -> None:
        if not self._require_project():
            return
        editors = [self.original_editor, self.cleaned_editor, self.rewrite_editor]
        text = editors[self.export_version.currentIndex()].toPlainText()
        destination, _ = QFileDialog.getSaveFileName(self, "导出 TXT", "文案.txt", "文本 (*.txt)")
        if destination:
            export_text(Path(destination), text)
            self.log(f"已导出：{destination}（{count_effective_characters(text)} 字）")

    def export_srt(self) -> None:
        if not self._require_project():
            return
        source = self.project_root / "transcript" / "subtitle.srt"
        if not source.exists():
            QMessageBox.information(self, "没有字幕", "请先完成离线转写。")
            return
        destination, _ = QFileDialog.getSaveFileName(self, "导出 SRT", "字幕.srt", "字幕 (*.srt)")
        if destination:
            shutil.copy2(source, destination)
            self.log(f"已导出：{destination}")

    def export_audio(self) -> None:
        if not self._require_project():
            return
        source = self.project_root / "tts" / "output.wav"
        if not source.exists():
            QMessageBox.information(self, "没有配音", "请先生成本地配音。")
            return
        destination, selected_filter = QFileDialog.getSaveFileName(
            self, "导出音频", "配音.wav", "WAV 音频 (*.wav);;MP3 音频 (*.mp3)"
        )
        if not destination:
            return
        target = Path(destination)
        if "MP3" in selected_filter or target.suffix.lower() == ".mp3":
            self.media_service.wav_to_mp3(source, target.with_suffix(".mp3"))
        else:
            shutil.copy2(source, target.with_suffix(".wav"))
        self.log(f"已导出音频：{destination}")
