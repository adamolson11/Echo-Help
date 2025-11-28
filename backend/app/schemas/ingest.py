from pydantic import BaseModel
from typing import List, Optional


class IngestMessage(BaseModel):
    author: str
    text: str
    timestamp: Optional[str] = None


class IngestThread(BaseModel):
    source: str
    external_id: str
    title: str
    resolved: bool
    resolution_notes: Optional[str] = None
    messages: List[IngestMessage]
