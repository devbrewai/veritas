"""Pydantic schemas for business registration document data extraction."""

from datetime import date

from pydantic import BaseModel, Field


class Director(BaseModel):
    """Individual director/officer information."""

    name: str
    title: str | None = Field(default=None, description="e.g., Director, CEO, Secretary")


class BusinessDocumentData(BaseModel):
    """Extracted business registration document data."""

    # Required fields from PRD
    company_name: str = Field(description="Registered company name")
    registration_number: str = Field(
        description="Company registration/incorporation number"
    )
    directors: list[Director] = Field(
        default_factory=list, description="List of directors/officers"
    )
    registration_date: date = Field(description="Date of incorporation/registration")

    # Optional enrichment fields
    business_type: str | None = Field(
        default=None, description="Entity type: LLC, Corporation, Partnership, etc."
    )
    registered_address: str | None = Field(
        default=None, description="Registered office address"
    )
    jurisdiction: str | None = Field(
        default=None, description="State/country of incorporation"
    )
    status: str | None = Field(
        default=None, description="Company status: Active, Dissolved, etc."
    )


class BusinessDocumentExtractionResult(BaseModel):
    """Full business document extraction result with status and errors."""

    success: bool
    data: BusinessDocumentData | None = None
    confidence: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
