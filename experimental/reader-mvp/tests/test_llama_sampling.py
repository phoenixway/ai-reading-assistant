from app.config import settings
from app.llama import LlamaClient
from app.reader import _extraction_chat


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "OK",
                    }
                }
            ]
        }


def test_chat_accepts_explicit_temperature_and_seed(monkeypatch):
    captured = {}

    client = LlamaClient("http://example.invalid")
    monkeypatch.setattr(
        client,
        "model_name",
        lambda: "test-model",
    )

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "app.llama.httpx.post",
        fake_post,
    )

    text, _ = client.chat(
        [{"role": "user", "content": "x"}],
        temperature=0.0,
        seed=123,
        cache_prompt=False,
    )

    assert text == "OK"
    assert captured["payload"]["temperature"] == 0.0
    assert captured["payload"]["seed"] == 123
    assert captured["payload"]["cache_prompt"] is False
    assert captured["payload"]["top_p"] == 1.0


def test_normal_chat_keeps_normal_temperature(monkeypatch):
    captured = {}

    client = LlamaClient("http://example.invalid")
    monkeypatch.setattr(
        client,
        "model_name",
        lambda: "test-model",
    )

    def fake_post(url, json, timeout):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "app.llama.httpx.post",
        fake_post,
    )

    client.chat(
        [{"role": "user", "content": "x"}]
    )

    assert (
        captured["payload"]["temperature"]
        == settings.temperature
    )
    assert "seed" not in captured["payload"]
    assert "cache_prompt" not in captured["payload"]


def test_extraction_gateway_is_deterministic():
    class Dummy:
        def __init__(self):
            self.kwargs = None

        def chat(self, messages, **kwargs):
            self.kwargs = kwargs
            return "OK", 0.0

    client = Dummy()

    text, elapsed = _extraction_chat(
        client,
        [{"role": "user", "content": "x"}],
    )

    assert text == "OK"
    assert elapsed == 0.0
    assert (
        client.kwargs["temperature"]
        == settings.extraction_temperature
        == 0.0
    )
    assert (
        client.kwargs["seed"]
        == settings.extraction_seed
        == 424242
    )
    assert client.kwargs["cache_prompt"] is False
