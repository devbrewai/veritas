"""Pydantic schemas for passport data extraction."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class PassportData(BaseModel):
    """Extracted passport data from MRZ."""

    # Required fields from MRZ
    document_type: str = Field(description="Document type code (P for passport)")
    issuing_country: str = Field(description="3-letter country code")
    surname: str
    given_names: str
    passport_number: str
    nationality: str = Field(description="3-letter nationality code")
    date_of_birth: date
    sex: Literal["M", "F", "X"] | None = None
    expiry_date: date

    # Optional fields
    personal_number: str | None = None

    # Raw MRZ lines for reference
    mrz_line1: str | None = Field(default=None, description="Raw MRZ line 1")
    mrz_line2: str | None = Field(default=None, description="Raw MRZ line 2")

    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name from given names and surname."""
        return f"{self.given_names} {self.surname}".strip()


class PassportExtractionResult(BaseModel):
    """Full passport extraction result with status and errors."""

    success: bool
    data: PassportData | None = None
    confidence: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
