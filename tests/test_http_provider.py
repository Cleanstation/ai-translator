import io
import json

import pytest

import ai_translator
from ai_translator import HTTPProvider


class FakeHTTPResponse:
    def __init__(self, payload):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        self.payload = payload.encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeHTTPError(ai_translator.urllib.error.HTTPError):
    def __init__(self, url: str, code: int, payload: str):
        super().__init__(url, code, "boom", hdrs=None, fp=io.BytesIO(payload.encode("utf-8")))


def test_http_provider_openai_posts_chat_completions_and_returns_text(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"電源板": "power-board"}'
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="openai",
        base_url="http://localhost:13305/v1",
        model="user.gemma-4-26B-A4B-it-GGUF",
        api_key="example-api-key",
        timeout=45,
    )

    output = provider.generate("請翻譯")

    assert output == '{"電源板": "power-board"}'
    assert captured["url"] == "http://localhost:13305/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer example-api-key"
    assert captured["body"]["model"] == "user.gemma-4-26B-A4B-it-GGUF"
    assert captured["body"]["messages"] == [{"role": "user", "content": "請翻譯"}]
    assert captured["timeout"] == 45


def test_http_provider_anthropic_posts_messages_and_returns_text(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "content": [
                    {"type": "text", "text": '{"電源板": "power-board"}'}
                ]
            }
        )

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="anthropic",
        base_url="http://localhost:13305",
        model="user.gemma-4-26B-A4B-it-GGUF",
        api_key="example-api-key",
        timeout=30,
    )

    output = provider.generate("請翻譯")

    assert output == '{"電源板": "power-board"}'
    assert captured["url"] == "http://localhost:13305/v1/messages"
    assert captured["headers"]["Authorization"] == "Bearer example-api-key"
    assert captured["headers"]["X-api-key"] == "example-api-key"
    assert captured["headers"]["Anthropic-version"] == "2023-06-01"
    assert captured["body"]["model"] == "user.gemma-4-26B-A4B-it-GGUF"
    assert captured["body"]["messages"] == [{"role": "user", "content": "請翻譯"}]
    assert captured["timeout"] == 30


def test_http_provider_raises_clear_error_for_http_error(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise FakeHTTPError(request.full_url, 401, '{"error":"bad auth"}')

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="openai",
        base_url="http://localhost:13305/v1",
        model="user.gemma-4-26B-A4B-it-GGUF",
        api_key="example-api-key",
    )

    with pytest.raises(RuntimeError, match=r"HTTP provider 請求失敗: 401"):
        provider.generate("請翻譯")


def test_http_provider_raises_clear_error_for_url_error(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise ai_translator.urllib.error.URLError("connection refused")

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="openai",
        base_url="http://localhost:13305/v1",
        model="user.gemma-4-26B-A4B-it-GGUF",
    )

    with pytest.raises(RuntimeError, match=r"HTTP provider 無法連線: connection refused"):
        provider.generate("請翻譯")


def test_http_provider_raises_clear_error_for_invalid_json_body(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return FakeHTTPResponse("not-json")

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="openai",
        base_url="http://localhost:13305/v1",
        model="user.gemma-4-26B-A4B-it-GGUF",
    )

    with pytest.raises(RuntimeError, match=r"HTTP provider 回應不是合法 JSON"):
        provider.generate("請翻譯")


def test_http_provider_raises_clear_error_for_unexpected_json_shape(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return FakeHTTPResponse([])

    monkeypatch.setattr(ai_translator.urllib_request, "urlopen", fake_urlopen)

    provider = HTTPProvider(
        protocol="openai",
        base_url="http://localhost:13305/v1",
        model="user.gemma-4-26B-A4B-it-GGUF",
    )

    with pytest.raises(RuntimeError, match=r"HTTP provider 回應格式錯誤"):
        provider.generate("請翻譯")
