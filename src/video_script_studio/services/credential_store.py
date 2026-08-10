from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


class AzureCredentialStore:
    """Persist the Azure key with Windows DPAPI for the current Windows user."""

    def __init__(self, path: Path | None = None) -> None:
        app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        self.path = path or app_data / "VideoScriptStudio" / "azure-settings.json"

    @staticmethod
    def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(data)
        blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        return blob, buffer

    @classmethod
    def protect(cls, plaintext: str) -> str:
        if os.name != "nt":
            raise RuntimeError("Azure 密钥加密存储仅支持 Windows。")
        source, source_buffer = cls._blob(plaintext.encode("utf-8"))
        output = _DataBlob()
        result = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
        )
        _ = source_buffer
        if not result:
            raise ctypes.WinError()
        try:
            encrypted = ctypes.string_at(output.pbData, output.cbData)
            return base64.b64encode(encrypted).decode("ascii")
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    @classmethod
    def unprotect(cls, protected: str) -> str:
        source, source_buffer = cls._blob(base64.b64decode(protected))
        output = _DataBlob()
        result = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
        )
        _ = source_buffer
        if not result:
            raise ctypes.WinError()
        try:
            return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(output.pbData)

    def save(self, key: str, region: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"region": region.strip(), "protected_key": self.protect(key.strip())}
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self) -> tuple[str, str] | None:
        if not self.path.is_file():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return self.unprotect(data["protected_key"]), str(data["region"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
