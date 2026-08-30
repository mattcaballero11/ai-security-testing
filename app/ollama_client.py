"""Thin async client over the Ollama HTTP API.

Deliberately not the ollama-python SDK: one fewer dependency to pin, and the
options block from section 3 of the build spec stays explicit in our code.
"""

from __future__ import annotations

import httpx

from app.config import Settings


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_host, timeout=settings.ollama_timeout
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float | None = None,
        seed: int | None = ...,
    ) -> dict:
        """One non-streaming chat completion.

        temperature=None and seed=... use the configured canonical values.
        Rate runs pass temperature=0.7, seed=None.
        Returns {"content": str, "eval_count": int, "total_duration_ns": int}.
        """
        options = self._s.gen.to_ollama(temperature=temperature, seed=seed)
        payload = {
            "model": self._s.ollama_model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama returned {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"could not reach Ollama at {self._s.ollama_host}: {exc}") from exc

        data = resp.json()
        return {
            "content": data.get("message", {}).get("content", ""),
            "eval_count": data.get("eval_count", 0),
            "prompt_eval_count": data.get("prompt_eval_count", 0),
            "total_duration_ns": data.get("total_duration", 0),
            "options": options,
        }

    async def resolve_digest(self) -> str:
        """Digest Ollama reports for the configured model tag, or '' if the tag
        is not present locally."""
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"could not reach Ollama at {self._s.ollama_host}: {exc}") from exc
        for model in resp.json().get("models", []):
            if model.get("name") == self._s.ollama_model:
                return model.get("digest", "")
        return ""
