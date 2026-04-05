from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    summary: str
    description: str
    source: str = "manual"
    project_key: str = "IT"
    priority: str | None = "medium"
