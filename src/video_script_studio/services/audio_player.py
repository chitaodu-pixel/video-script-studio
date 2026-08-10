from __future__ import annotations

import ctypes
import os
from pathlib import Path

from video_script_studio.domain.errors import ExternalProcessError


class WindowsAudioPlayer:
    """Small in-process MP3 player backed by the Windows multimedia API."""

    ALIAS = "vss_audio_preview"

    def __init__(self) -> None:
        if os.name != "nt":
            self._winmm = None
            return
        self._winmm = ctypes.WinDLL("winmm")
        self._winmm.mciSendStringW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_void_p,
        ]
        self._winmm.mciSendStringW.restype = ctypes.c_uint
        self._winmm.mciGetErrorStringW.argtypes = [
            ctypes.c_uint,
            ctypes.c_wchar_p,
            ctypes.c_uint,
        ]

    def _send(self, command: str) -> str:
        if self._winmm is None:
            raise ExternalProcessError("当前系统不支持内置音频试听。")
        output = ctypes.create_unicode_buffer(512)
        code = self._winmm.mciSendStringW(command, output, len(output), None)
        if code:
            detail = ctypes.create_unicode_buffer(512)
            self._winmm.mciGetErrorStringW(code, detail, len(detail))
            raise ExternalProcessError(detail.value or f"音频播放失败（错误 {code}）")
        return output.value

    def play(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"音频文件不存在：{path}")
        self.stop()
        self._send(f'open "{path}" type mpegvideo alias {self.ALIAS}')
        try:
            self._send(f"play {self.ALIAS} from 0")
        except Exception:
            self._send(f"close {self.ALIAS}")
            raise

    def stop(self) -> None:
        if self._winmm is None:
            return
        # Closing an alias that is not open returns an error, which is harmless here.
        output = ctypes.create_unicode_buffer(1)
        self._winmm.mciSendStringW(f"close {self.ALIAS}", output, len(output), None)
