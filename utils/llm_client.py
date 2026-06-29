"""LLM client with rule-based fallback for offline operation."""

from __future__ import annotations

import json
from typing import Any

from config import get_settings
from utils.logging_config import logger


class LLMClient:
    """Unified LLM interface supporting OpenAI with deterministic fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any = None
        if self.settings.llm_available:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.settings.openai_api_key)
            except Exception as exc:
                logger.warning("OpenAI client init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.available:
            logger.info("LLM unavailable, using rule-based fallback")
            return fallback_response or {"response": "Analysis completed using rule-based engine."}

        try:
            response = self._client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            logger.error("LLM invocation failed: %s", exc)
            if self.settings.llm_fallback_enabled and fallback_response:
                return fallback_response
            raise


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
