from __future__ import annotations

from sqlmodel import SQLModel


class Meta(SQLModel):
    kind: str
    version: str
