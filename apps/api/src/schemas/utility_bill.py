"""Pydantic schemas for utility bill data extraction."""

from datetime import date

from pydantic import BaseModel, Field, computed_field


class UtilityBillData(BaseModel):
    """Extracted utility bill data."""

    # Required fields from PRD
    name: str = Field(description="Account holder name")
    address: str = Field(description="Service address")
    bill_date: date = Field(description="Bill/statement date")
    utility_provider: str = Field(description="Utility company name")

    # Optional enrichment fields
    account_number: str | None = Field(default=None, description="Account number")
    amount_due: float | None = Field(default=None, description="Amount due")
    due_date: date | None = Field(default=None, description="Payment due date")
    utility_type: str | None = Field(
        default=None, description="Type: electricity, gas, water, internet, phone"
    )

    @computed_field
    @property
    def address_lines(self) -> list[str]:
        """Split address into lines for display."""
        return [line.strip() for line in self.address.split(",")]


class UtilityBillExtractionResult(BaseModel):
    """Full utility bill extraction result with status and errors."""

    success: bool
    data: UtilityBillData | None = None
    confidence: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
