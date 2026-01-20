"""Passport MRZ parsing using the mrz library."""

from datetime import date

from mrz.checker.td3 import TD3CodeChecker

from src.schemas.passport import PassportData, PassportExtractionResult


class PassportParser:
    """Parses passport MRZ data into structured format.

    Supports TD3 format (standard passport with 2 lines of 44 characters).
    """

    @staticmethod
    def clean_mrz_text(text: str) -> list[str]:
        """Clean OCR output and split into MRZ lines.

        Args:
            text: Raw OCR text from MRZ region.

        Returns:
            List of cleaned MRZ lines.
        """
        # Normalize to uppercase and remove spaces
        text = text.upper().replace(" ", "")

        # Split into lines and filter empty
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # TD3 passports have 2 lines of 44 characters each
        # If we got a single long line, try to split it
        if len(lines) == 1 and len(lines[0]) >= 88:
            full = lines[0]
            lines = [full[:44], full[44:88]]

        # Validate and normalize line lengths
        valid_lines = []
        for line in lines:
            # Remove any non-MRZ characters that might have slipped through
            cleaned = "".join(c for c in line if c.isalnum() or c == "<")

            # TD3 lines should be 44 chars
            if len(cleaned) >= 44:
                valid_lines.append(cleaned[:44])
            elif len(cleaned) >= 30:
                # Pad shorter lines with < (filler character)
                valid_lines.append(cleaned.ljust(44, "<"))

        return valid_lines

    @staticmethod
    def _parse_mrz_date(date_str: str, is_expiry: bool = False) -> date | None:
        """Parse YYMMDD format to date object.

        Args:
            date_str: Date string in YYMMDD format.
            is_expiry: If True, assume 2000s century; otherwise use heuristics.

        Returns:
            Parsed date or None if invalid.
        """
        if not date_str or len(date_str) != 6:
            return None

        try:
            year = int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])

            # Handle century
            # For expiry dates, almost always 2000s
            # For birth dates, use heuristic: >30 = 1900s, <=30 = 2000s
            if is_expiry:
                year += 2000
            elif year > 30:
                year += 1900
            else:
                year += 2000

            return date(year, month, day)
        except ValueError:
            return None

    def parse(self, mrz_text: str, confidence: float = 0.0) -> PassportExtractionResult:
        """Parse MRZ text into structured passport data.

        Args:
            mrz_text: Raw OCR text from MRZ region.
            confidence: OCR confidence score (0-1).

        Returns:
            PassportExtractionResult with parsed data or errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            lines = self.clean_mrz_text(mrz_text)

            if len(lines) < 2:
                return PassportExtractionResult(
                    success=False,
                    confidence=confidence,
                    errors=[
                        f"Could not extract 2 MRZ lines from OCR output. Found {len(lines)} lines."
                    ],
                )

            # Combine lines for TD3 checker (expects 89-char string with newline separator)
            mrz_code = "\n".join(lines[:2])

            if len(mrz_code) != 89:
                return PassportExtractionResult(
                    success=False,
                    confidence=confidence,
                    errors=[
                        f"MRZ code length is {len(mrz_code)}, expected 89 characters (44 + newline + 44)."
                    ],
                )

            # Use mrz library for validation and parsing
            try:
                checker = TD3CodeChecker(mrz_code)
                fields = checker.fields()

                # Check validation results
                if not checker.result:
                    warnings.append(
                        "MRZ checksum validation failed - data may be inaccurate"
                    )

                # Parse dates
                dob = self._parse_mrz_date(fields.birth_date, is_expiry=False)
                expiry = self._parse_mrz_date(fields.expiry_date, is_expiry=True)

                if not dob:
                    errors.append(f"Could not parse date of birth: {fields.birth_date}")
                if not expiry:
                    errors.append(f"Could not parse expiry date: {fields.expiry_date}")

                # If critical dates couldn't be parsed, fail
                if not dob or not expiry:
                    return PassportExtractionResult(
                        success=False,
                        confidence=confidence,
                        errors=errors,
                        warnings=warnings,
                    )

                # Clean up name fields (replace < with space)
                surname = fields.surname.replace("<", " ").strip()
                given_names = fields.name.replace("<", " ").strip()

                # Handle sex field
                sex = fields.sex if fields.sex in ("M", "F", "X") else None

                # Clean personal number
                personal_number = fields.optional_data.replace("<", "").strip() or None

                passport_data = PassportData(
                    document_type=fields.document_type.strip(),
                    issuing_country=fields.country,
                    surname=surname,
                    given_names=given_names,
                    passport_number=fields.document_number.replace("<", "").strip(),
                    nationality=fields.nationality,
                    date_of_birth=dob,
                    sex=sex,
                    expiry_date=expiry,
                    personal_number=personal_number,
                    mrz_line1=lines[0],
                    mrz_line2=lines[1],
                )

                return PassportExtractionResult(
                    success=True,
                    data=passport_data,
                    confidence=confidence,
                    errors=errors,
                    warnings=warnings,
                )

            except Exception as e:
                errors.append(f"MRZ parsing error: {e!s}")
                return PassportExtractionResult(
                    success=False,
                    confidence=confidence,
                    errors=errors,
                )

        except Exception as e:
            return PassportExtractionResult(
                success=False,
                confidence=confidence,
                errors=[f"Unexpected error: {e!s}"],
            )
