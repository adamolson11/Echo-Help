from pydantic import BaseModel
from typing import Any, List


class AskEchoRequest(BaseModel):
    q: str
    limit: int = 5


class AskEchoResponse(BaseModel):
    query: str
    answer: str
    results: List[Any]
