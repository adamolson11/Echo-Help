from datetime import datetime

from sqlmodel import Field, SQLModel


class Embedding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    object_type: str  # "ticket", "document", "concept"
    object_id: int
    model_name: str
    vector_json: str  # Store as JSON string of floats, e.g. "[0.12, -0.3, ...]"
    created_at: datetime = Field(default_factory=datetime.utcnow)
