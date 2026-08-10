import json
import urllib.error

from video_script_studio.services.azure_tts import AzureTTSService, AzureVoice


def test_azure_request_retries_direct_when_stale_proxy_fails(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"direct-response"

    class DirectOpener:
        def open(self, request, timeout=60):
            assert request.full_url.startswith("https://eastasia.")
            assert request.host == "eastasia.tts.speech.microsoft.com"
            return Response()

    def stale_proxy(request, **_kwargs):
        request.set_proxy("127.0.0.1:1080", "https")
        raise urllib.error.URLError("proxy refused connection")

    monkeypatch.setattr("urllib.request.urlopen", stale_proxy)
    monkeypatch.setattr("urllib.request.build_opener", lambda *_handlers: DirectOpener())
    request = __import__("urllib.request", fromlist=["Request"]).Request(
        "https://eastasia.tts.speech.microsoft.com/cognitiveservices/voices/list"
    )

    assert AzureTTSService._request(request) == b"direct-response"


def test_azure_voice_list_keeps_chinese_neural_voices(monkeypatch) -> None:
    service = AzureTTSService()
    payload = [
        {
            "Locale": "zh-CN",
            "ShortName": "zh-CN-XiaoxiaoNeural",
            "LocalName": "晓晓",
            "Gender": "Female",
        },
        {
            "Locale": "en-US",
            "ShortName": "en-US-JennyNeural",
            "LocalName": "Jenny",
            "Gender": "Female",
        },
    ]
    monkeypatch.setattr(service, "_request", lambda _request, timeout=60: json.dumps(payload).encode())
    voices = service.voices("secret", "eastasia")
    assert len(voices) == 1
    assert voices[0].short_name == "zh-CN-XiaoxiaoNeural"
    assert "女声" in voices[0].display_name


def test_azure_synthesis_uses_ssml_controls_and_writes_mp3(monkeypatch, tmp_path) -> None:
    service = AzureTTSService()
    captured = {}

    def fake_request(request, timeout=60):
        captured["body"] = request.data.decode("utf-8")
        captured["format"] = request.headers["X-microsoft-outputformat"]
        return b"mp3-data"

    monkeypatch.setattr(service, "_request", fake_request)
    destination = tmp_path / "speech.mp3"
    voice = AzureVoice("晓晓", "zh-CN-XiaoxiaoNeural", "zh-CN")
    service.synthesize_mp3("A&B", destination, "secret", "eastasia", voice, 15, -5, 80)
    assert destination.read_bytes() == b"mp3-data"
    assert "A&amp;B" in captured["body"]
    assert 'rate="+15%"' in captured["body"]
    assert 'pitch="-5%"' in captured["body"]
    assert 'volume="80%"' in captured["body"]
    assert captured["format"] == "audio-24khz-96kbitrate-mono-mp3"
