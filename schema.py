from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class EvidenceRef(BaseModel):
    review_id: str = Field(min_length=1)
    snippet: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Point(BaseModel):
    point: str = Field(min_length=1)
    evidence: List[EvidenceRef] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class MomsVerdict(BaseModel):
    summary_en: str = Field(min_length=1)
    summary_ar: str = Field(min_length=1)

    pros: List[Point]
    cons: List[Point]

    disagreements: List[str]

    confidence_score: float = Field(ge=0.0, le=1.0)

    insufficient_data_flags: List[str]

    user_warning: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("summary_en", "summary_ar")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value

    @model_validator(mode="after")
    def check_warning_alignment(self):
        if self.confidence_score < 0.5 and not self.user_warning:
            raise ValueError("user_warning is required when confidence_score is below 0.5")
        return self
