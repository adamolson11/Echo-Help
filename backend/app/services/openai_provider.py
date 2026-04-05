from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping

import httpx

from .llm_provider import LLMProvider, ProviderAnswer

logger = logging.getLogger("uvicorn.error")


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 15.0,
        base_url: str = "https://api.openai.com/v1/chat/completions",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url

    def generate(self, *, problem: str, context: Mapping[str, object]) -> ProviderAnswer:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the server-side provider seam for E.C.O. "
                        "Generate a concise operator answer grounded only in the supplied local context. "
                        "Do not claim system access, ticket writes, Jira actions, or hidden evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Problem:\n{problem}\n\n"
                        "Local context JSON:\n"
                        f"{json.dumps(context, ensure_ascii=True)}\n\n"
                        "Return 2-4 short sentences with a concrete next move and a caution if certainty is low."
                    ),
                },
            ],
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = _extract_message_content(data)
        if not content:
            raise ValueError("OpenAI provider returned an empty message")

        return ProviderAnswer(
            answer_text=content,
            mode="openai_fallback",
            confidence=None,
            sources=[],
        )


def build_default_llm_provider_from_env() -> LLMProvider | None:
    enabled = os.getenv("ECHOHELP_OPENAI_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ECHOHELP_OPENAI_API_KEY")
    if not enabled:
        return None
    if not api_key:
        logger.warning("ECHOHELP_OPENAI_ENABLED is set but no OpenAI API key was provided")
        return None

    return OpenAIProvider(
        api_key=api_key,
        model=os.getenv("ECHOHELP_OPENAI_MODEL", "gpt-4.1-mini"),
    )


def _extract_message_content(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""
