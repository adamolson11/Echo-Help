from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderAnswer:
    answer_text: str
    mode: str
    confidence: float | None = None
    sources: list[str] | None = None


class LLMProvider(Protocol):
    def generate(self, *, problem: str, context: Mapping[str, object]) -> ProviderAnswer:
        ...
