from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from .llm_provider import ProviderAnswer

_SYSTEM_PROMPT = (
    "You are EchoHelp's optional server-side fallback assistant. "
    "Provide concise IT support guidance, prefer actionable next steps, "
    "and do not claim access to systems or evidence that are not present in the prompt."
)


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            elif isinstance(item, str) and item.strip():
                parts.append(item.strip())
        return "\n".join(parts).strip()
    return ""


def _extract_answer_text(payload: object) -> str:
    if not isinstance(payload, Mapping):
        raise ValueError("OpenAI response payload must be an object")

    choices = payload.get("choices")
    if not isinstance(choices, Sequence) or not choices:
        raise ValueError("OpenAI response did not include choices")

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise ValueError("OpenAI response choice was invalid")

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise ValueError("OpenAI response message was missing")

    answer_text = _coerce_text(message.get("content"))
    if not answer_text:
        raise ValueError("OpenAI response content was empty")
    return answer_text


class OpenAIProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client

    def _build_user_prompt(self, *, problem: str, context: Mapping[str, object] | None) -> str:
        parts = [f"User problem:\n{problem.strip()}"]

        if context:
            local_answer = context.get("local_answer")
            if isinstance(local_answer, str) and local_answer.strip():
                parts.append(f"Current local fallback answer:\n{local_answer.strip()}")

            sources = context.get("sources")
            if isinstance(sources, Sequence) and not isinstance(sources, (str, bytes)):
                normalized_sources = [str(item).strip() for item in sources if str(item).strip()]
                if normalized_sources:
                    parts.append("Available sources:\n- " + "\n- ".join(normalized_sources))

        parts.append(
            "Return a short answer suitable for a support engineer. "
            "If the prompt lacks environment-specific evidence, say so plainly."
        )
        return "\n\n".join(parts)

    def _request(self, client: httpx.Client, *, payload: dict[str, object]) -> object:
        response = client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def generate(self, problem: str, context: Mapping[str, object] | None = None) -> ProviderAnswer:
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(problem=problem, context=context)},
            ],
        }

        if self._client is not None:
            data = self._request(self._client, payload=payload)
        else:
            with httpx.Client(timeout=self._timeout) as client:
                data = self._request(client, payload=payload)

        return ProviderAnswer(
            answer_text=_extract_answer_text(data),
            mode="openai",
            sources=[],
        )
