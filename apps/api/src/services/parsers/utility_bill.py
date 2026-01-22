"""Utility bill parsing from OCR text using regex patterns."""

import re
from datetime import date

from dateutil import parser as date_parser
from dateutil.parser import ParserError

from src.schemas.utility_bill import UtilityBillData, UtilityBillExtractionResult


class UtilityBillParser:
    """Parses utility bill OCR text into structured data.

    Uses regex patterns to extract key fields from unstructured OCR text.
    Utility bills have no standard format, so we use multiple patterns
    and heuristics to find fields.
    """

    # Common utility provider names for detection
    KNOWN_PROVIDERS = [
        # US Electric
        "Con Edison",
        "ConEd",
        "Pacific Gas",
        "PG&E",
        "Duke Energy",
        "National Grid",
        "Xcel Energy",
        "Dominion Energy",
        "Southern California Edison",
        "SCE",
        "ComEd",
        "Eversource",
        "Florida Power",
        "FPL",
        "Georgia Power",
        "AEP",
        "Entergy",
        "PPL",
        "Ameren",
        # US Gas
        "SoCalGas",
        "Atmos Energy",
        "CenterPoint",
        "NiSource",
        "Southwest Gas",
        # US Water
        "American Water",
        "Aqua America",
        "California Water",
        # Telecom/Internet
        "AT&T",
        "Verizon",
        "Comcast",
        "Xfinity",
        "Spectrum",
        "T-Mobile",
        "Cox",
        "CenturyLink",
        "Frontier",
        # International
        "British Gas",
        "EDF Energy",
        "E.ON",
        "Scottish Power",
        "SSE",
        "Thames Water",
        "Vodafone",
        "BT",
        "Virgin Media",
    ]

    # Regex patterns for field extraction (case-insensitive)
    NAME_PATTERNS = [
        # Labeled name fields
        r"(?:Account\s*Holder|Customer\s*Name|Name|Bill\s*To|Service\s*For|Account\s*Name)[:\s]+([A-Z][A-Za-z\s\-']+?)(?:\n|$|Account)",
        # Name followed by address (name on its own line)
        r"^([A-Z][A-Z\s\-']+)\n\d+\s+[A-Za-z]",
    ]

    ADDRESS_PATTERNS = [
        # US format: 123 Main St, City, ST 12345
        r"(\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl|Circle|Cir)[.,]?\s*(?:Apt|Suite|Unit|#)?\s*[A-Za-z0-9]*[,.\s]+[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)",
        # Labeled address
        r"(?:Service\s*Address|Address|Location)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)",
        # Multi-line address after label
        r"(?:Service\s*Address|Billing\s*Address|Address)[:\s]*\n(.+?\d{5}(?:-\d{4})?)",
    ]

    DATE_PATTERNS = [
        # Labeled date fields
        r"(?:Statement\s*Date|Bill\s*Date|Date\s*of\s*Bill|Invoice\s*Date|Billing\s*Date)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:Statement\s*Date|Bill\s*Date|Invoice\s*Date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        # Date patterns without label
        r"(?:Statement|Bill|Invoice)\s+(?:for\s+)?([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
    ]

    DUE_DATE_PATTERNS = [
        r"(?:Due\s*Date|Payment\s*Due|Pay\s*By)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:Due\s*Date|Payment\s*Due)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
    ]

    ACCOUNT_NUMBER_PATTERNS = [
        r"(?:Account\s*(?:Number|No|#)|Acct\s*(?:Number|No|#)?)[:\s#]*([A-Z0-9\-]+)",
        r"(?:Customer\s*(?:Number|No|#)|Cust\s*(?:Number|No|#)?)[:\s#]*([A-Z0-9\-]+)",
    ]

    AMOUNT_PATTERNS = [
        r"(?:Amount\s*Due|Total\s*Due|Balance\s*Due|Total\s*Amount|Current\s*Charges)[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"(?:Total)[:\s]*\$\s*([\d,]+\.\d{2})",
    ]

    def parse(self, ocr_text: str, confidence: float = 0.0) -> UtilityBillExtractionResult:
        """Parse OCR text into utility bill data.

        Args:
            ocr_text: Raw OCR text from document.
            confidence: OCR confidence score (0-1).

        Returns:
            UtilityBillExtractionResult with parsed data or errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not ocr_text or not ocr_text.strip():
            return UtilityBillExtractionResult(
                success=False,
                confidence=confidence,
                errors=["No text extracted from document"],
            )

        # Extract fields
        name = self._extract_name(ocr_text)
        address = self._extract_address(ocr_text)
        bill_date = self._extract_bill_date(ocr_text)
        provider = self._extract_provider(ocr_text)

        # Validate required fields
        if not name:
            errors.append("Could not extract account holder name")
        if not address:
            errors.append("Could not extract service address")
        if not bill_date:
            errors.append("Could not extract bill date")
        if not provider:
            warnings.append("Could not identify utility provider - using 'Unknown'")
            provider = "Unknown Provider"

        if errors:
            return UtilityBillExtractionResult(
                success=False,
                confidence=confidence,
                errors=errors,
                warnings=warnings,
            )

        # Extract optional fields
        account_number = self._extract_account_number(ocr_text)
        amount_due = self._extract_amount(ocr_text)
        due_date = self._extract_due_date(ocr_text)
        utility_type = self._infer_utility_type(ocr_text, provider)

        # Build result
        data = UtilityBillData(
            name=name,
            address=address,
            bill_date=bill_date,
            utility_provider=provider,
            account_number=account_number,
            amount_due=amount_due,
            due_date=due_date,
            utility_type=utility_type,
        )

        return UtilityBillExtractionResult(
            success=True,
            data=data,
            confidence=confidence,
            warnings=warnings,
        )

    def _extract_name(self, text: str) -> str | None:
        """Extract account holder name from text."""
        for pattern in self.NAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r"\s+", " ", name)  # Normalize whitespace
                if len(name) >= 2 and len(name) <= 100:
                    return name
        return None

    def _extract_address(self, text: str) -> str | None:
        """Extract service address from text."""
        for pattern in self.ADDRESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                # Clean up address
                address = re.sub(r"\s+", " ", address)  # Normalize whitespace
                address = re.sub(r"\n", ", ", address)  # Replace newlines with commas
                if len(address) >= 10:
                    return address
        return None

    def _extract_bill_date(self, text: str) -> date | None:
        """Extract bill/statement date from text."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                parsed = self._parse_date(date_str)
                if parsed:
                    return parsed
        return None

    def _extract_due_date(self, text: str) -> date | None:
        """Extract payment due date from text."""
        for pattern in self.DUE_DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                parsed = self._parse_date(date_str)
                if parsed:
                    return parsed
        return None

    def _extract_provider(self, text: str) -> str | None:
        """Extract utility provider name from text."""
        # First, try to find known providers
        text_upper = text.upper()
        for provider in self.KNOWN_PROVIDERS:
            if provider.upper() in text_upper:
                return provider

        # Try to find provider from common patterns
        provider_patterns = [
            r"^([A-Z][A-Za-z\s&]+(?:Electric|Gas|Water|Energy|Power|Utility|Telecom|Communications))",
            r"(?:From|Billed\s*By)[:\s]+([A-Z][A-Za-z\s&]+?)(?:\n|$)",
        ]
        for pattern in provider_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                provider = match.group(1).strip()
                if len(provider) >= 3 and len(provider) <= 100:
                    return provider

        return None

    def _extract_account_number(self, text: str) -> str | None:
        """Extract account number from text."""
        for pattern in self.ACCOUNT_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                account = match.group(1).strip()
                if len(account) >= 4:
                    return account
        return None

    def _extract_amount(self, text: str) -> float | None:
        """Extract amount due from text."""
        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).strip()
                try:
                    # Remove commas and convert
                    amount = float(amount_str.replace(",", ""))
                    if amount >= 0:
                        return amount
                except ValueError:
                    continue
        return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse a date string into a date object.

        Uses dateutil for flexible parsing of various formats.
        """
        try:
            parsed = date_parser.parse(date_str, dayfirst=False)
            return parsed.date()
        except (ParserError, ValueError, OverflowError):
            return None

    def _infer_utility_type(self, text: str, provider: str | None) -> str | None:
        """Infer utility type from text content and provider name."""
        text_lower = (text + " " + (provider or "")).lower()

        type_keywords = {
            "electricity": ["electric", "kwh", "kilowatt", "power", "watt"],
            "gas": ["natural gas", "therm", "ccf", "mcf", "gas usage"],
            "water": ["water", "sewer", "gallons", "cubic feet", "ccf water"],
            "internet": ["internet", "broadband", "wifi", "mbps", "gbps", "data plan"],
            "phone": ["phone", "mobile", "cellular", "wireless", "minutes", "text"],
            "cable": ["cable", "tv", "television", "channels"],
        }

        for utility_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return utility_type

        return None
