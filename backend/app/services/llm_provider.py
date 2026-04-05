from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class ProviderAnswer:
    answer_text: str
    mode: str
    confidence: float | None = None
    sources: list[str] | None = None


class LLMProvider(Protocol):
    def generate(self, problem: str, context: dict[str, object]) -> ProviderAnswer: ...


@dataclass(frozen=True)
class OpenAIProviderConfig:
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 15.0


def _env_flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _extract_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


class OpenAIProvider:
    def __init__(self, config: OpenAIProviderConfig) -> None:
        self._config = config

    def generate(self, problem: str, context: dict[str, object]) -> ProviderAnswer:
        payload = {
            "model": self._config.model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are assisting E.C.O. Keep answers concise, operational, and bounded to the provided context. "
                        "Do not invent system-specific facts. If context is weak, say so plainly."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Problem:\n{problem}\n\n"
                        f"Context:\n{context}\n\n"
                        "Return a short operator-ready answer only."
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self._config.timeout_seconds) as client:
            response = client.post(f"{self._config.base_url.rstrip('/')}/responses", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        answer_text = _extract_output_text(data)
        if not answer_text:
            raise ValueError("openai provider returned no answer text")

        return ProviderAnswer(answer_text=answer_text, mode="openai")


def get_configured_llm_provider() -> LLMProvider | None:
    if not _env_flag("ECHOHELP_OPENAI_ENABLED"):
        return None

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        logger.warning("openai provider enabled but OPENAI_API_KEY is missing; falling back to local templates")
        return None

    model = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    base_url = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
    timeout_value = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "15").strip() or "15"
    try:
        timeout_seconds = float(timeout_value)
    except ValueError:
        timeout_seconds = 15.0

    return OpenAIProvider(
        OpenAIProviderConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    )
