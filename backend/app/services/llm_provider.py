from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


@dataclass(frozen=True)
class ProviderAnswer:
    answer_text: str
    mode: str
    confidence: float | None = None
    sources: list[str] | None = None


class LLMProvider(Protocol):
    def generate(self, problem: str, context: Mapping[str, object] | None = None) -> ProviderAnswer: ...


def _openai_enabled() -> bool:
    value = os.getenv("ECHOHELP_OPENAI_ENABLED", "").strip().lower()
    return value in _TRUE_VALUES


def get_llm_provider() -> LLMProvider | None:
    if not _openai_enabled():
        return None

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    from .openai_provider import OpenAIProvider

    return OpenAIProvider(
        api_key=api_key,
        model=os.getenv("ECHOHELP_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
    )
