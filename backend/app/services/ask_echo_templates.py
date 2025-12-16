from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AskEchoTemplates:
    grounded_prefix: str = (
        "Based on your past tickets, here are the most relevant related issues:\n"
    )
    grounded_fallback: str = (
        "I found some tickets that may be related, but couldn't format them clearly."
    )
    ungrounded_answer: str = (
        "I couldn't find any matching tickets or prior solutions in your history for this question. "
        "Here's general guidance based on typical IT issues, but it's not specific to your environment."
    )
    experimental_note: str = (
        "\n\nNote: This is experimental AI output — verify details before applying fixes."
    )
