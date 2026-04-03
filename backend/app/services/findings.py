from backend.app.ai.normalize import normalize_phrase
from backend.app.schemas.findings import NormalizedFinding
from backend.app.schemas.ingest import IngestThread
from backend.app.schemas.tickets import TicketCreate

_CATEGORY_KEYWORDS_BY_CATEGORY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("authentication", ("login", "password", "auth", "sso")),
    ("connectivity", ("vpn", "disconnect", "connection", "network")),
    ("build", ("build", "deploy", "pipeline", "ci")),
)

_PRODUCT_AREAS = {
    "authentication": "account_access",
    "connectivity": "connectivity",
    "build": "delivery_pipeline",
}

_HIGH_SEVERITY_KEYWORDS = {
    "cant",
    "cannot",
    "disconnect",
    "down",
    "drops",
    "error",
    "failed",
    "failure",
    "timeout",
}

_PRIORITY_BY_SEVERITY = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_FULL_CONFIDENCE = 1.0
_PARTIAL_CONFIDENCE = 0.5


def _thread_evidence(thread: IngestThread) -> list[str]:
    evidence = [thread.title.strip()]
    evidence.extend(
        f"[{message.author}] {message.text.strip()}"
        for message in thread.messages
        if message.text.strip()
    )
    return evidence


def _source_or_fallback(source: str) -> str:
    return source.strip() or "support"


def _project_key(source: str) -> str:
    return _source_or_fallback(source).upper()


def _category_for_text(normalized_text: str) -> str:
    for category, keywords in _CATEGORY_KEYWORDS_BY_CATEGORY:
        if any(keyword in normalized_text for keyword in keywords):
            return category
    return "support"


def _severity_for_text(normalized_text: str, *, resolved: bool) -> str:
    if any(keyword in normalized_text for keyword in _HIGH_SEVERITY_KEYWORDS):
        return "high"
    if resolved:
        return "low"
    return "medium"


def normalize_ingest_thread(thread: IngestThread) -> NormalizedFinding:
    normalized_text = normalize_phrase(
        "\n".join([thread.title, *[message.text for message in thread.messages]])
    )
    category = _category_for_text(normalized_text)
    severity = _severity_for_text(normalized_text, resolved=thread.resolved)
    evidence = _thread_evidence(thread)
    return NormalizedFinding(
        finding_id=f"{thread.source}:{thread.external_id}",
        source=thread.source,
        source_record_id=thread.external_id,
        summary=thread.title.strip(),
        category=category,
        severity=severity,
        confidence=_FULL_CONFIDENCE if len(evidence) > 1 else _PARTIAL_CONFIDENCE,
        evidence=evidence,
        product_area=_PRODUCT_AREAS.get(category, _source_or_fallback(thread.source)),
        status="resolved" if thread.resolved else "needs-review",
    )


def emit_ticket_draft(finding: NormalizedFinding) -> TicketCreate:
    description_lines = [
        f"Finding ID: {finding.finding_id}",
        f"Category: {finding.category}",
        f"Severity: {finding.severity}",
        f"Product area: {finding.product_area}",
        f"Status: {finding.status}",
        f"Confidence: {finding.confidence:.2f}",
        "Evidence:",
        *[f"- {item}" for item in finding.evidence],
    ]
    return TicketCreate(
        summary=finding.summary,
        description="\n".join(description_lines),
        source=finding.source,
        project_key=_project_key(finding.source),
        status="closed" if finding.status == "resolved" else "open",
        priority=_PRIORITY_BY_SEVERITY[finding.severity],
        external_key=finding.source_record_id,
    )
