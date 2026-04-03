from pydantic import BaseModel, Field


class NormalizedFinding(BaseModel):
    finding_id: str = Field(min_length=3)
    source: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    product_area: str = Field(min_length=1)
    status: str = Field(min_length=1)
