from __future__ import annotations
import time
import httpx
from .config import settings

class LlamaError(RuntimeError):
    pass

class LlamaClient:
    def __init__(self, base_url: str | None = None):
        self.base = (base_url or settings.llama_url).rstrip('/')

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base}/health", timeout=3)
            return {"ok": r.status_code == 200, "status": r.status_code, "body": r.text[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def model_name(self) -> str:
        try:
            r = httpx.get(f"{self.base}/v1/models", timeout=5)
            r.raise_for_status()
            return r.json()["data"][0]["id"]
        except Exception:
            return "local-model"

    def token_count(self, text: str) -> int:
        try:
            r = httpx.post(f"{self.base}/tokenize", json={"content": text, "add_special": False}, timeout=20)
            r.raise_for_status()
            return len(r.json()["tokens"])
        except Exception:
            # conservative fallback for mixed Latin/Cyrillic prose
            return max(1, int(len(text) / 3.6))

    def chat(
        self,
        messages: list[dict],
        *,
        max_tokens: int | None = None,
        reasoning: str | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        cache_prompt: bool | None = None,
    ) -> tuple[str, float]:
        payload = {
            "model": self.model_name(),
            "messages": messages,
            "max_tokens": max_tokens or settings.max_output_tokens,
            "temperature": (
                settings.temperature
                if temperature is None
                else temperature
            ),
            "top_p": 1.0,
            "reasoning_effort": reasoning or settings.reasoning_effort,
            "stream": False,
        }

        if seed is not None:
            payload["seed"] = seed

        if cache_prompt is not None:
            payload["cache_prompt"] = cache_prompt

        t0 = time.perf_counter()
        r = httpx.post(f"{self.base}/v1/chat/completions", json=payload, timeout=600)
        elapsed = time.perf_counter() - t0
        if r.status_code >= 400:
            raise LlamaError(f"llama-server {r.status_code}: {r.text[:1000]}")
        data = r.json()
        try:
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("final") or ""
        except Exception as e:
            raise LlamaError(f"Unexpected response: {data}") from e
        return content.strip(), elapsed
