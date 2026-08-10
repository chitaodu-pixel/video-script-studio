from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from video_script_studio.domain.errors import ExternalProcessError


@dataclass(frozen=True, slots=True)
class AzureVoice:
    display_name: str
    short_name: str
    locale: str


class AzureTTSService:
    """Microsoft Azure neural TTS through the official REST endpoints."""

    @staticmethod
    def _endpoint(region: str, path: str) -> str:
        region = region.strip().lower()
        if not region or not region.replace("-", "").isalnum():
            raise ValueError("Azure 区域格式不正确。")
        return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/{path}"

    @staticmethod
    def _request(request: urllib.request.Request, timeout: int = 60) -> bytes:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise ExternalProcessError(
                f"Azure 语音服务返回 {exc.code}：{detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as proxy_exc:
            # Proxy environment variables can remain after desktop proxy software is closed.
            # Retry once without any proxy before reporting a network failure.
            try:
                direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with direct.open(request, timeout=timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace").strip()
                raise ExternalProcessError(
                    f"Azure 语音服务返回 {exc.code}：{detail or exc.reason}"
                ) from exc
            except urllib.error.URLError as direct_exc:
                raise ExternalProcessError(
                    f"无法连接 Azure 语音服务（代理和直连均失败）：{direct_exc.reason}"
                ) from direct_exc

    def voices(self, key: str, region: str, language_prefix: str = "zh-") -> list[AzureVoice]:
        if not key.strip():
            raise ValueError("请先填写 Azure Speech 密钥。")
        request = urllib.request.Request(
            self._endpoint(region, "voices/list"),
            headers={"Ocp-Apim-Subscription-Key": key.strip()},
            method="GET",
        )
        data = json.loads(self._request(request).decode("utf-8"))
        output = []
        for item in data:
            locale = str(item.get("Locale", ""))
            if language_prefix and not locale.startswith(language_prefix):
                continue
            short_name = str(item.get("ShortName", ""))
            if not short_name:
                continue
            local_name = str(item.get("LocalName") or item.get("DisplayName") or short_name)
            gender = "女声" if item.get("Gender") == "Female" else "男声"
            output.append(AzureVoice(f"{local_name}（{gender}） · {short_name}", short_name, locale))
        return sorted(output, key=lambda voice: (voice.locale, voice.display_name))

    def synthesize_mp3(
        self,
        text: str,
        destination: Path,
        key: str,
        region: str,
        voice: AzureVoice,
        rate: int = 0,
        pitch: int = 0,
        volume: int = 100,
    ) -> None:
        if not key.strip():
            raise ValueError("请先填写 Azure Speech 密钥。")
        destination.parent.mkdir(parents=True, exist_ok=True)
        ssml = (
            f'<speak version="1.0" xml:lang="{escape(voice.locale)}">'
            f'<voice name="{escape(voice.short_name)}">'
            f'<prosody rate="{rate:+d}%" pitch="{pitch:+d}%" volume="{volume}%">'
            f"{escape(text)}</prosody></voice></speak>"
        )
        request = urllib.request.Request(
            self._endpoint(region, "v1"),
            data=ssml.encode("utf-8"),
            headers={
                "Ocp-Apim-Subscription-Key": key.strip(),
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                "User-Agent": "VideoScriptStudio",
            },
            method="POST",
        )
        audio = self._request(request, timeout=600)
        if not audio:
            raise ExternalProcessError("Azure 没有返回音频数据。")
        destination.write_bytes(audio)
