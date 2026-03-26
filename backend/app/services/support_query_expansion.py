from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_SPACE_RE = re.compile(r"\s+")

_PASSWORD_RESET_ALIASES = (
    "password reset",
    "reset password",
    "forgot password",
    "forgot my password",
    "reset my password",
    "reset account password",
    "account password",
)

_LOGIN_ACCESS_ALIASES = (
    "login",
    "log in",
    "sign in",
    "signin",
    "cant log in",
    "can't log in",
    "cannot log in",
    "unable to log in",
    "account access",
    "locked out",
    "unlock account",
)


def normalize_support_query(text: str) -> str:
    value = (text or "").strip().lower()
    if not value:
        return ""
    value = (
        value.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("/", " ")
        .replace("-", " ")
    )
    value = _NON_ALNUM_RE.sub(" ", value)
    return _SPACE_RE.sub(" ", value).strip()


def query_tokens(text: str) -> tuple[str, ...]:
    normalized = normalize_support_query(text)
    if not normalized:
        return ()
    return tuple(token for token in normalized.split(" ") if token)


def expand_support_query(query: str) -> list[str]:
    normalized = normalize_support_query(query)
    if not normalized:
        return []

    seen: set[str] = set()
    expanded: list[str] = []

    def add(value: str) -> None:
        item = normalize_support_query(value)
        if item and item not in seen:
            seen.add(item)
            expanded.append(item)

    add(query)
    add(normalized)

    tokens = set(query_tokens(normalized))

    has_password_reset_intent = (
        {"password", "reset"}.issubset(tokens)
        or "forgot password" in normalized
        or "forgot my password" in normalized
        or ("password" in tokens and "forgot" in tokens)
    )
    has_login_intent = (
        "login" in tokens
        or {"log", "in"}.issubset(tokens)
        or {"sign", "in"}.issubset(tokens)
        or "signin" in tokens
        or "locked" in tokens
        or ("account" in tokens and ("access" in tokens or "unlock" in tokens))
    )

    if has_password_reset_intent:
        for alias in _PASSWORD_RESET_ALIASES:
            add(alias)
        add("account access")
        add("login help")

    if has_login_intent or has_password_reset_intent:
        for alias in _LOGIN_ACCESS_ALIASES:
            add(alias)

    return expanded


def search_query_variants(query: str) -> list[str]:
    raw = (query or "").strip()
    if not raw:
        return []

    seen: set[str] = set()
    variants: list[str] = []

    def add(value: str) -> None:
        item = (value or "").strip()
        if item and item not in seen:
            seen.add(item)
            variants.append(item)

    add(raw)
    add(raw.lower())
    for item in expand_support_query(raw):
        add(item)
    return variants


def keyword_match_score(*, query: str, haystack: str) -> float:
    normalized_haystack = normalize_support_query(haystack)
    if not normalized_haystack:
        return 0.0

    expanded = expand_support_query(query)
    if not expanded:
        return 0.0

    best = 0.0
    primary = expanded[0]
    if primary and primary in normalized_haystack:
        best = 1.0

    for alias in expanded[1:]:
        if alias and alias in normalized_haystack:
            best = max(best, 0.92)

    haystack_tokens = set(query_tokens(normalized_haystack))
    query_token_set = set(query_tokens(primary))
    if query_token_set and haystack_tokens:
        overlap = len(query_token_set & haystack_tokens) / float(len(query_token_set))
        if overlap > 0.0:
            best = max(best, 0.25 + 0.5 * overlap)

    expanded_token_set: set[str] = set()
    for alias in expanded[1:]:
        expanded_token_set.update(query_tokens(alias))

    if expanded_token_set and haystack_tokens:
        overlap = len(expanded_token_set & haystack_tokens) / float(len(expanded_token_set))
        if overlap > 0.0:
            best = max(best, 0.2 + 0.75 * overlap)

    return min(best, 1.0)
