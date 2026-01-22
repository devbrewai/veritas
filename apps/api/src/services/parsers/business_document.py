"""Business registration document parsing from OCR text using regex patterns."""

import re
from datetime import date

from dateutil import parser as date_parser
from dateutil.parser import ParserError

from src.schemas.business_document import (
    BusinessDocumentData,
    BusinessDocumentExtractionResult,
    Director,
)


class BusinessDocumentParser:
    """Parses business registration document OCR text into structured data.

    Supports common formats:
    - Certificate of Incorporation
    - Certificate of Formation (LLC)
    - Certificate of Organization
    - Business Registration Certificate
    - Articles of Incorporation
    """

    # Business entity type keywords
    ENTITY_TYPES = {
        "corporation": ["corporation", "corp", "inc", "incorporated"],
        "llc": ["llc", "l.l.c.", "limited liability company"],
        "partnership": ["partnership", "lp", "llp", "limited partnership"],
        "sole proprietorship": ["sole proprietor", "dba", "doing business as"],
        "nonprofit": ["nonprofit", "non-profit", "501(c)", "not for profit"],
    }

    # US State names and abbreviations
    US_STATES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
        "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
        "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
        "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
        "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
        "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
        "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    }

    # Regex patterns for company name extraction
    COMPANY_NAME_PATTERNS = [
        # Certificate patterns
        r"(?:This\s+is\s+to\s+certify\s+that|Certificate\s+of\s+(?:Incorporation|Formation|Organization)\s+of)\s+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|,\s*(?:a|has|is))",
        r"(?:Company\s*Name|Entity\s*Name|Name\s*of\s*(?:Company|Corporation|Entity)|Business\s*Name)[:\s]+([A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
        # Articles of Incorporation
        r"(?:ARTICLES\s+OF\s+INCORPORATION|CERTIFICATE\s+OF\s+INCORPORATION)\s+OF\s+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
        # Name field in form
        r"(?:^|\n)Name[:\s]+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
    ]

    # Regex patterns for registration number
    REGISTRATION_NUMBER_PATTERNS = [
        r"(?:File\s*Number|Entity\s*(?:Number|ID)|Registration\s*(?:Number|No)|Document\s*Number|Charter\s*Number|Corp\s*ID)[:\s#]*([A-Z0-9\-]+)",
        r"(?:EIN|Tax\s*ID|Federal\s*Tax\s*ID)[:\s]*(\d{2}-\d{7})",
        r"(?:Number|No\.?)[:\s]*([A-Z]?\d{6,12})",
    ]

    # Regex patterns for registration date
    DATE_PATTERNS = [
        r"(?:Date\s*of\s*(?:Incorporation|Formation|Registration|Organization)|Incorporated|Filed|Formed|Organized|Registered)\s*(?:on)?[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:Date\s*of\s*(?:Incorporation|Formation)|Filed|Incorporated)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        r"(?:on\s+the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+,?\s*\d{4})",
        r"(?:Effective\s*Date|Date)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    ]

    # Regex patterns for directors
    DIRECTORS_PATTERNS = [
        # Labeled directors section
        r"(?:Directors?|Officers?|Managers?|Members?|Organizers?)[:\s]+(.+?)(?:Registered|Address|Article|$)",
        # Individual director entries
        r"(?:Director|Officer|President|Secretary|Treasurer|CEO|CFO|Manager)[:\s]+([A-Z][A-Za-z\s\-']+?)(?:\n|,|$)",
    ]

    # Address patterns
    ADDRESS_PATTERNS = [
        r"(?:Registered\s*(?:Office|Agent)?\s*Address|Principal\s*(?:Office|Place)|Business\s*Address)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)",
        r"(?:Address)[:\s]+(\d+\s+.+?\d{5}(?:-\d{4})?)",
    ]

    def parse(
        self, ocr_text: str, confidence: float = 0.0
    ) -> BusinessDocumentExtractionResult:
        """Parse OCR text into business document data.

        Args:
            ocr_text: Raw OCR text from document.
            confidence: OCR confidence score (0-1).

        Returns:
            BusinessDocumentExtractionResult with parsed data or errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not ocr_text or not ocr_text.strip():
            return BusinessDocumentExtractionResult(
                success=False,
                confidence=confidence,
                errors=["No text extracted from document"],
            )

        # Extract required fields
        company_name = self._extract_company_name(ocr_text)
        registration_number = self._extract_registration_number(ocr_text)
        registration_date = self._extract_registration_date(ocr_text)
        directors = self._extract_directors(ocr_text)

        # Validate required fields
        if not company_name:
            errors.append("Could not extract company name")
        if not registration_number:
            errors.append("Could not extract registration number")
        if not registration_date:
            errors.append("Could not extract registration date")
        if not directors:
            warnings.append("Could not extract directors list")

        if errors:
            return BusinessDocumentExtractionResult(
                success=False,
                confidence=confidence,
                errors=errors,
                warnings=warnings,
            )

        # Extract optional fields
        business_type = self._extract_business_type(ocr_text)
        registered_address = self._extract_address(ocr_text)
        jurisdiction = self._extract_jurisdiction(ocr_text)
        status = self._extract_status(ocr_text)

        # Build result
        data = BusinessDocumentData(
            company_name=company_name,
            registration_number=registration_number,
            directors=directors,
            registration_date=registration_date,
            business_type=business_type,
            registered_address=registered_address,
            jurisdiction=jurisdiction,
            status=status,
        )

        return BusinessDocumentExtractionResult(
            success=True,
            data=data,
            confidence=confidence,
            warnings=warnings,
        )

    def _extract_company_name(self, text: str) -> str | None:
        """Extract company name from text."""
        for pattern in self.COMPANY_NAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r"\s+", " ", name)  # Normalize whitespace
                name = name.rstrip(",.")  # Remove trailing punctuation
                if len(name) >= 2 and len(name) <= 200:
                    return name
        return None

    def _extract_registration_number(self, text: str) -> str | None:
        """Extract registration/file number from text."""
        for pattern in self.REGISTRATION_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                number = match.group(1).strip()
                if len(number) >= 4:
                    return number
        return None

    def _extract_registration_date(self, text: str) -> date | None:
        """Extract registration/incorporation date from text."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                parsed = self._parse_date(date_str)
                if parsed:
                    return parsed
        return None

    def _extract_directors(self, text: str) -> list[Director]:
        """Extract directors/officers from text."""
        directors: list[Director] = []
        seen_names: set[str] = set()

        # Try to find a directors section
        for pattern in self.DIRECTORS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section = match.group(1)
                # Parse individual names from section
                names = self._parse_names_from_section(section)
                for name, title in names:
                    name_lower = name.lower()
                    if name_lower not in seen_names:
                        seen_names.add(name_lower)
                        directors.append(Director(name=name, title=title))

        # Also look for individual officer mentions
        officer_pattern = r"(President|Secretary|Treasurer|CEO|CFO|COO|Director|Manager|Member)[:\s]+([A-Z][A-Za-z\s\-']+?)(?:\n|,|;|$)"
        for match in re.finditer(officer_pattern, text, re.IGNORECASE):
            title = match.group(1).strip().title()
            name = match.group(2).strip()
            name = re.sub(r"\s+", " ", name)
            name_lower = name.lower()

            if len(name) >= 2 and len(name) <= 100 and name_lower not in seen_names:
                seen_names.add(name_lower)
                directors.append(Director(name=name, title=title))

        return directors

    def _parse_names_from_section(self, section: str) -> list[tuple[str, str | None]]:
        """Parse names and titles from a directors section."""
        results: list[tuple[str, str | None]] = []

        # Split by common delimiters
        parts = re.split(r"[,;\n]", section)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for "Name - Title" or "Name, Title" format
            title_match = re.match(
                r"([A-Z][A-Za-z\s\-']+?)[\s\-,]+(?:as\s+)?(President|Secretary|Treasurer|Director|CEO|CFO|Manager|Member)$",
                part,
                re.IGNORECASE,
            )
            if title_match:
                name = title_match.group(1).strip()
                title = title_match.group(2).strip().title()
                if len(name) >= 2:
                    results.append((name, title))
            else:
                # Just a name
                name_match = re.match(r"([A-Z][A-Za-z\s\-']+)", part)
                if name_match:
                    name = name_match.group(1).strip()
                    name = re.sub(r"\s+", " ", name)
                    if len(name) >= 2 and len(name) <= 100:
                        results.append((name, None))

        return results

    def _extract_business_type(self, text: str) -> str | None:
        """Extract business entity type from text."""
        text_lower = text.lower()

        # Check for specific entity type patterns first
        type_patterns = [
            (r"limited\s+liability\s+company|llc|l\.l\.c\.", "LLC"),
            (r"corporation|corp\.|inc\.|incorporated", "Corporation"),
            (r"limited\s+partnership|l\.p\.", "Limited Partnership"),
            (r"general\s+partnership", "General Partnership"),
            (r"sole\s+proprietor", "Sole Proprietorship"),
            (r"nonprofit|non-profit|501\(c\)", "Nonprofit"),
        ]

        for pattern, entity_type in type_patterns:
            if re.search(pattern, text_lower):
                return entity_type

        return None

    def _extract_address(self, text: str) -> str | None:
        """Extract registered address from text."""
        for pattern in self.ADDRESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                address = re.sub(r"\s+", " ", address)
                address = re.sub(r"\n", ", ", address)
                if len(address) >= 10:
                    return address
        return None

    def _extract_jurisdiction(self, text: str) -> str | None:
        """Extract state/country of incorporation from text."""
        # Check for "State of X" pattern
        state_match = re.search(
            r"State\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text
        )
        if state_match:
            state = state_match.group(1).strip()
            return state

        # Check for state abbreviations
        for abbr, name in self.US_STATES.items():
            # Look for "filed in DE" or "Delaware corporation" patterns
            if re.search(rf"\b{abbr}\b", text) or re.search(
                rf"\b{name}\b", text, re.IGNORECASE
            ):
                return name

        return None

    def _extract_status(self, text: str) -> str | None:
        """Extract company status from text."""
        status_patterns = [
            (r"Status[:\s]+(\w+)", None),
            (r"\b(Active|Good Standing|In Good Standing)\b", "Active"),
            (r"\b(Dissolved|Inactive|Revoked|Cancelled)\b", "Dissolved"),
            (r"\b(Pending|Processing)\b", "Pending"),
        ]

        for pattern, default_status in status_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return default_status or match.group(1).strip().title()

        return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse a date string into a date object."""
        # Clean up ordinal suffixes
        date_str = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_str)

        try:
            parsed = date_parser.parse(date_str, dayfirst=False)
            return parsed.date()
        except (ParserError, ValueError, OverflowError):
            return None
