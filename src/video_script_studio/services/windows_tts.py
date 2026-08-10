from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from video_script_studio.domain.errors import ExternalProcessError
from video_script_studio.services.media import MediaService
from video_script_studio.services.subprocess_utils import hidden_subprocess_kwargs


class WindowsTTSService:
    """Use the built-in Windows System.Speech voices without a cloud API."""

    VOICE_COMMAND = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Speech; "
        "$s=[System.Speech.Synthesis.SpeechSynthesizer]::new(); "
        "$s.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name} | ConvertTo-Json -Compress"
    )
    SPEAK_COMMAND = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=[System.Speech.Synthesis.SpeechSynthesizer]::new(); "
        "if($env:VSS_VOICE){$s.SelectVoice($env:VSS_VOICE)}; "
        "$text=[IO.File]::ReadAllText($env:VSS_TEXT,[Text.Encoding]::UTF8); "
        "$safe=[Security.SecurityElement]::Escape($text); "
        "$voice=[Security.SecurityElement]::Escape($env:VSS_VOICE); "
        "$ssml=\"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' \"+"
        "\"xml:lang='zh-CN'><voice name='$voice'><prosody rate='$env:VSS_RATE%' \"+"
        "\"pitch='$env:VSS_PITCH%' volume='$env:VSS_VOLUME%'>$safe</prosody></voice></speak>\"; "
        "$s.SetOutputToWaveFile($env:VSS_WAV); $s.SpeakSsml($ssml); $s.Dispose()"
    )

    def __init__(self, media_service: MediaService | None = None) -> None:
        self.media = media_service or MediaService()

    def voices(self) -> list[str]:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", self.VOICE_COMMAND],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode != 0:
            raise ExternalProcessError(result.stderr.strip() or "无法读取 Windows 声优")
        raw = result.stdout.strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]

    def synthesize_mp3(
        self,
        text: str,
        destination: Path,
        voice: str | None = None,
        rate: int = 0,
        pitch: int = 0,
        volume: int = 100,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="video-script-studio-tts-") as temp:
            temp_path = Path(temp)
            text_path = temp_path / "speech.txt"
            wav_path = temp_path / "speech.wav"
            text_path.write_text(text, encoding="utf-8")
            environment = os.environ.copy()
            environment.update(
                {
                    "VSS_TEXT": str(text_path),
                    "VSS_WAV": str(wav_path),
                    "VSS_VOICE": voice or "",
                    "VSS_RATE": str(max(-50, min(50, rate))),
                    "VSS_PITCH": str(max(-20, min(20, pitch))),
                    "VSS_VOLUME": str(max(0, min(100, volume))),
                }
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", self.SPEAK_COMMAND],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
                env=environment,
                check=False,
                **hidden_subprocess_kwargs(),
            )
            if result.returncode != 0 or not wav_path.exists():
                raise ExternalProcessError(result.stderr.strip() or "Windows 语音合成失败")
            self.media.wav_to_mp3(wav_path, destination)
