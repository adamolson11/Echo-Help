
from pydantic import BaseModel


class IngestMessage(BaseModel):
    author: str
    text: str
    timestamp: str | None = None


class IngestThread(BaseModel):
    source: str
    external_id: str
    title: str
    resolved: bool
    resolution_notes: str | None = None
    messages: list[IngestMessage]
