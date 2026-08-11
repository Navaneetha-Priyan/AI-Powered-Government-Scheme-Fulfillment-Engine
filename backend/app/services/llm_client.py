"""Lightweight LLM client for Phase 4 - Multilingual & Intent Normalization.

Uses httpx (already a project dependency) to call a local Ollama endpoint that
exposes the OpenAI-compatible ``/v1/chat/completions`` API. No external LLM SDK
or API key is required.

The client is intentionally thin and focused: it only performs a chat completion
and returns the raw text content. Parsing/validation of the structured response
is the responsibility of ``TextNormalizationService``.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import LLMUnavailableError

logger = get_logger(__name__)


class LLMClient:
    """Minimal OpenAI-compatible chat client backed by a local Ollama server."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        logger.info(
            "LLMClient configured (base_url=%s, model=%s, timeout=%ss)",
            self.base_url,
            self.model,
            self.timeout,
        )

    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request and return the assistant's text.

        Raises:
            LLMUnavailableError: if the endpoint is unreachable, times out, or
                returns a non-2xx status.
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(self.timeout)) as client:
                response = client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("LLM request timed out after %ss: %s", self.timeout, exc)
            raise LLMUnavailableError("LLM request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("LLM request failed: %s", exc)
            raise LLMUnavailableError("LLM request failed") from exc

        if response.status_code != 200:
            logger.warning("LLM returned HTTP %s", response.status_code)
            raise LLMUnavailableError(f"LLM returned HTTP {response.status_code}")

        try:
            data = response.json()
            content: Optional[str] = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("LLM returned a malformed completion payload")
            raise LLMUnavailableError("LLM returned a malformed completion payload") from exc

        if not content:
            logger.warning("LLM returned an empty completion")
            raise LLMUnavailableError("LLM returned an empty completion")
        print("\n" + "=" * 60)
        print("🧠 QWEN RAW RESPONSE")
        print("=" * 60)
        print(content)
        print("=" * 60 + "\n")
        return content.strip()


def get_llm_client() -> LLMClient:
    """Return a shared LLMClient instance (cached)."""
    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _factory() -> LLMClient:
        return LLMClient()

    return _factory()
