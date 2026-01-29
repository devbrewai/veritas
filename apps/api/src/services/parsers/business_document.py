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

    # Written number to digit mapping (for Indian MCA dates)
    WRITTEN_ORDINALS = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
        "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
        "nineteenth": 19, "twentieth": 20, "twenty-first": 21, "twenty-second": 22,
        "twenty-third": 23, "twenty-fourth": 24, "twenty-fifth": 25,
        "twenty-sixth": 26, "twenty-seventh": 27, "twenty-eighth": 28,
        "twenty-ninth": 29, "thirtieth": 30, "thirty-first": 31,
    }

    WRITTEN_YEARS = {
        "two thousand nineteen": 2019, "two thousand twenty": 2020,
        "two thousand twenty-one": 2021, "two thousand twenty one": 2021,
        "two thousand twenty-two": 2022, "two thousand twenty two": 2022,
        "two thousand twenty-three": 2023, "two thousand twenty three": 2023,
        "two thousand twenty-four": 2024, "two thousand twenty four": 2024,
        "two thousand twenty-five": 2025, "two thousand twenty five": 2025,
        "two thousand twenty-six": 2026, "two thousand twenty six": 2026,
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

    # Regex patterns for company name extraction (order matters - more specific patterns first)
    COMPANY_NAME_PATTERNS = [
        # Indian MCA Certificate of Incorporation: "I hereby certify that [NAME] is incorporated"
        r"I\s+hereby\s+certify\s+that\s+([A-Z][A-Z0-9\s&.,'\-]+(?:PRIVATE\s+)?LIMITED)\s+is\s+incorporated",
        # Nigerian CAC format: "I hereby certify that\nCOMPANY NAME" (OCR may have typos)
        r"(?:I\s*hereby\s*cert[il]fy\s*that|TD\s*hereby\s*cestify\s*that)\s*\n?\s*([A-Z][A-Z0-9\s&.,'/\-]+?)(?:\n\n|\nis\s|\nés)",
        # Mexican format: "A NOMBRE DE: COMPANY NAME"
        r"A\s+NOMBRE\s+DE[:\s]+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
        # Kenyan/African business registration format: "business name of\nCOMPANY NAME"
        r"(?:business\s+name\s+of|trading\s+as|t/a)\s*\n?\s*([A-Z][A-Z0-9\s&.,'\-]+?)(?:\n|at\s|$)",
        # Certificate patterns
        r"(?:This\s+is\s+to\s+certify\s+that|Certificate\s+of\s+(?:Incorporation|Formation|Organization)\s+of)\s+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|,\s*(?:a|has|is))",
        # Articles of Incorporation
        r"(?:ARTICLES\s+OF\s+INCORPORATION|CERTIFICATE\s+OF\s+INCORPORATION)\s+OF\s+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
        # Labeled name field (but not "name of" which would match the Kenyan format)
        r"(?:Company\s*Name|Entity\s*Name|Name\s*of\s*(?:Company|Corporation|Entity))[:\s]+([A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
        # Name field in form
        r"(?:^|\n)Name[:\s]+([A-Z][A-Za-z0-9\s&.,'\-]+?)(?:\n|$)",
    ]

    # Regex patterns for registration number
    REGISTRATION_NUMBER_PATTERNS = [
        # Indian CIN (Corporate Identity Number) - 21 characters: U51909DL2021FTC381930
        r"Corporate\s+Identity\s+Number[^:]*:\s*([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
        r"\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b",
        r"(?:File\s*Number|Entity\s*(?:Number|ID)|Registration\s*(?:Number|No)|Document\s*Number|Charter\s*Number|Corp\s*ID)[:\s#]*([A-Z0-9\-]+)",
        r"(?:EIN|Tax\s*ID|Federal\s*Tax\s*ID)[:\s]*(\d{2}-\d{7})",
        # Nigerian CAC format: "BN 2962929" or "CRBN 09965846"
        r"\b(BN\s*\d{6,10})\b",
        r"\b(CRBN\s*\d{6,10})\b",
        # Mexican Folio Mercantil format
        r"FOLIO\s+MERCANTIL\s+ELECTRONICO\s+(\d+)",
        # Kenyan business number format: BN-XXXXXXXX
        r"(?:Business\s*No|Business\s*Number)[:\s.]*([A-Z]{2}-[A-Z0-9]+)",
        r"\bNumber\s+([A-Z]{2}-[A-Z0-9]+)",
        r"(?:Number|No\.?)[:\s]*([A-Z]?\d{6,12})",
    ]

    # Regex patterns for registration date
    DATE_PATTERNS = [
        r"(?:Date\s*of\s*(?:Incorporation|Formation|Registration|Organization)|Incorporated|Filed|Formed|Organized|Registered)\s*(?:on)?[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:Date\s*of\s*(?:Incorporation|Formation)|Filed|Incorporated)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        # Indian MCA format: "this Fourth day of June Two thousand twenty-one"
        r"this\s+([A-Za-z]+\s+day\s+of\s+[A-Za-z]+\s+[A-Za-z\s\-]+?)(?:\.|$)",
        # Nigerian CAC format: "Dated this 11th day of April, 2019"
        r"Dated\s+this\s+(\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+,?\s*\d{4})",
        # "on the 15th day of March, 2022" pattern
        r"on\s+the\s+(\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+,?\s*\d{4})",
        # "on March 15, 2020" pattern (standalone)
        r"\bon\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        # "on 23-6-2022" pattern (DD-M-YYYY)
        r"\bon\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        # Mexican format: "FECHA DE REGISTRO: DD/MM/YYYY"
        r"FECHA\s+DE\s+REGISTRO[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
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

    def _convert_written_date(self, date_str: str) -> str | None:
        """Convert written date format to parseable format.

        E.g., "Fourth day of June Two thousand twenty-one" -> "4 June 2021"
        """
        date_lower = date_str.lower().strip()

        # Try to extract day (ordinal word)
        day = None
        for word, num in self.WRITTEN_ORDINALS.items():
            if date_lower.startswith(word):
                day = num
                date_lower = date_lower[len(word):].strip()
                break

        if not day:
            return None

        # Remove "day of" if present
        date_lower = re.sub(r"^\s*day\s+of\s+", "", date_lower)

        # Extract month
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        month = None
        for i, m in enumerate(months, 1):
            if date_lower.startswith(m):
                month = i
                date_lower = date_lower[len(m):].strip()
                break

        if not month:
            return None

        # Extract year (written format) - check longer strings first
        year = None
        # Sort by length descending to match longer strings first
        for written, num in sorted(self.WRITTEN_YEARS.items(), key=lambda x: len(x[0]), reverse=True):
            if written in date_lower:
                year = num
                break

        if not year:
            return None

        return f"{day} {months[month-1].title()} {year}"

    def _parse_date(self, date_str: str) -> date | None:
        """Parse a date string into a date object."""
        # First, try to convert written date format (Indian MCA style)
        if re.search(r"[a-zA-Z]+\s+day\s+of", date_str, re.IGNORECASE):
            converted = self._convert_written_date(date_str)
            if converted:
                try:
                    parsed = date_parser.parse(converted)
                    return parsed.date()
                except (ParserError, ValueError, OverflowError):
                    pass

        # Clean up ordinal suffixes (e.g., "15th" -> "15")
        date_str = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_str)
        # Clean up "day of" phrasing (e.g., "15 day of March" -> "15 March")
        date_str = re.sub(r"\s+day\s+of\s+", " ", date_str, flags=re.IGNORECASE)

        # Check if format looks like DD-M-YYYY or DD/M/YYYY (day first)
        # If first number > 12, it's definitely day-first
        day_first_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", date_str)
        if day_first_match:
            first_num = int(day_first_match.group(1))
            if first_num > 12:
                # Definitely day-first format
                try:
                    parsed = date_parser.parse(date_str, dayfirst=True)
                    return parsed.date()
                except (ParserError, ValueError, OverflowError):
                    pass

        # Try default parsing (month-first for US format)
        try:
            parsed = date_parser.parse(date_str, dayfirst=False)
            return parsed.date()
        except (ParserError, ValueError, OverflowError):
            pass

        # Fallback: try day-first parsing
        try:
            parsed = date_parser.parse(date_str, dayfirst=True)
            return parsed.date()
        except (ParserError, ValueError, OverflowError):
            return None
