from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

_log = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
_DEFAULT_OPENAI_TIMEOUT_SECONDS = 10.0
_PROVIDER_CONFIDENCE_THRESHOLD = 0.75


@dataclass(frozen=True)
class ProviderAnswer:
    answer_text: str
    mode: str
    confidence: float | None = None
    sources: list[str] | None = None


@dataclass(frozen=True)
class WorkItem:
    id: str
    title: str
    summary: str | None = None
    source: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class OutcomeRecord:
    problem: str
    recommendation_id: str
    recommendation_title: str
    outcome_status: str
    completed_step_ids: list[str]
    execution_notes: str | None = None
    reusable_learning: str | None = None


class LLMProvider(Protocol):
    def generate(
        self,
        problem: str,
        context: Sequence[Mapping[str, str]],
    ) -> ProviderAnswer | None: ...


class WorkItemSource(Protocol):
    def search(self, query: str, limit: int) -> list[WorkItem]: ...


class NullLLMProvider:
    def generate(
        self,
        problem: str,
        context: Sequence[Mapping[str, str]],
    ) -> ProviderAnswer | None:
        return None


class OpenAILLMProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = _DEFAULT_OPENAI_MODEL,
        base_url: str = _DEFAULT_OPENAI_BASE_URL,
        timeout_seconds: float = _DEFAULT_OPENAI_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        problem: str,
        context: Sequence[Mapping[str, str]],
    ) -> ProviderAnswer | None:
        cleaned_problem = problem.strip()
        if not cleaned_problem:
            return None

        context_lines: list[str] = []
        for item in context:
            label = str(item.get("label", "")).strip()
            value = str(item.get("value", "")).strip()
            if not value:
                continue
            prefix = f"{label}: " if label else ""
            context_lines.append(f"- {prefix}{value}")

        user_prompt = "\n".join(
            [
                "Problem:",
                cleaned_problem,
                "",
                "Local memory context:",
                *(context_lines or ["- No local memory context was available."]),
                "",
                (
                    "Return one concise operator answer. Use the local memory context first, "
                    "do not invent writeback steps, and do not mention that you are an AI model."
                ),
            ]
        )

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 220,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a bounded operations assistant. Prefer grounded, reversible next steps and concise language.",
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return ProviderAnswer(
            answer_text=content.strip(),
            mode="provider_openai",
            sources=["openai"],
        )


def build_llm_provider_from_env() -> LLMProvider:
    provider_name = os.getenv("ECHO_FLYWHEEL_PROVIDER", "").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if provider_name != "openai" or not api_key:
        return NullLLMProvider()
    model = os.getenv("OPENAI_MODEL", "").strip() or _DEFAULT_OPENAI_MODEL
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or _DEFAULT_OPENAI_BASE_URL
    timeout_raw = os.getenv("ECHO_FLYWHEEL_OPENAI_TIMEOUT_SECONDS", "").strip()
    timeout_seconds = _DEFAULT_OPENAI_TIMEOUT_SECONDS
    if timeout_raw:
        try:
            timeout_seconds = max(1.0, float(timeout_raw))
        except ValueError:
            _log.warning("Invalid ECHO_FLYWHEEL_OPENAI_TIMEOUT_SECONDS=%s; using default", timeout_raw)
    return OpenAILLMProvider(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


def maybe_generate_provider_answer(
    *,
    provider: LLMProvider,
    problem: str,
    local_answer: str,
    local_confidence: float,
    sources: Sequence[str],
) -> ProviderAnswer | None:
    if sources and local_confidence >= _PROVIDER_CONFIDENCE_THRESHOLD:
        return None

    context: list[dict[str, str]] = []
    if local_answer.strip():
        context.append({"label": "local_answer", "value": local_answer.strip()})
    for source in sources[:4]:
        cleaned_source = str(source).strip()
        if cleaned_source:
            context.append({"label": "source", "value": cleaned_source})

    try:
        return provider.generate(problem, context)
    except httpx.HTTPError as exc:
        _log.warning("Provider seam request failed: %s", exc)
    except Exception:
        _log.exception("Provider seam execution failed")
    return None
