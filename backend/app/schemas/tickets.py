from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    summary: str = Field(min_length=3)
    description: str = Field(min_length=3)
    source: str = Field(default="manual", min_length=2)
    project_key: str = Field(default="ECHO", min_length=2)
    status: str = Field(default="open", min_length=2)
    priority: str | None = None
    external_key: str | None = None
