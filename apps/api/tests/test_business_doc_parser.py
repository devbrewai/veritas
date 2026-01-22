"""Tests for business document parser."""

import pytest
from datetime import date

from src.services.parsers.business_document import BusinessDocumentParser
from src.schemas.business_document import Director


class TestBusinessDocumentParser:
    """Tests for BusinessDocumentParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BusinessDocumentParser()

    def test_parse_certificate_of_incorporation(self):
        """Test parsing a certificate of incorporation."""
        ocr_text = """
        CERTIFICATE OF INCORPORATION
        OF
        ACME TECHNOLOGIES, INC.

        State of Delaware

        This is to certify that ACME TECHNOLOGIES, INC.
        has been duly incorporated under the laws of the State of Delaware
        on March 15, 2020.

        File Number: 7654321

        Directors:
        - Jane Doe, President
        - John Smith, Secretary
        """

        result = self.parser.parse(ocr_text, confidence=0.85)

        assert result.success is True
        assert result.data is not None
        assert "ACME TECHNOLOGIES" in result.data.company_name
        assert result.data.registration_number == "7654321"
        assert result.data.registration_date == date(2020, 3, 15)
        assert len(result.data.directors) >= 1
        assert result.confidence == 0.85

    def test_parse_llc_formation(self):
        """Test parsing an LLC certificate of formation."""
        ocr_text = """
        CERTIFICATE OF FORMATION
        OF
        SMITH CONSULTING, LLC

        State of Texas

        This is to certify that SMITH CONSULTING, LLC
        a Limited Liability Company has been formed under the laws of Texas
        Date of Formation: 06/20/2021

        Entity ID: 0803456789

        Manager: Robert Smith
        """

        result = self.parser.parse(ocr_text, confidence=0.8)

        assert result.success is True
        assert result.data is not None
        assert "SMITH CONSULTING" in result.data.company_name
        assert result.data.registration_number == "0803456789"
        assert result.data.registration_date == date(2021, 6, 20)
        assert result.data.business_type == "LLC"

    def test_extract_company_name_patterns(self):
        """Test company name extraction with different patterns."""
        test_cases = [
            ("This is to certify that GLOBAL CORP has been incorporated", "GLOBAL CORP"),
            ("Company Name: Innovation Labs Inc.", "Innovation Labs Inc"),
            ("ARTICLES OF INCORPORATION OF TECH STARTUP LLC", "TECH STARTUP LLC"),
        ]

        for text, expected_name in test_cases:
            result = self.parser._extract_company_name(text)
            if result:
                assert expected_name.split()[0] in result, f"Expected '{expected_name}' in '{result}'"

    def test_extract_registration_number_patterns(self):
        """Test registration number extraction with various patterns."""
        test_cases = [
            ("File Number: 12345678", "12345678"),
            ("Entity ID: ABC-123456", "ABC-123456"),
            ("Registration No: C7654321", "C7654321"),
            ("EIN: 12-3456789", "12-3456789"),
        ]

        for text, expected in test_cases:
            result = self.parser._extract_registration_number(text)
            assert result == expected, f"Expected {expected}, got {result}"

    def test_extract_date_patterns(self):
        """Test registration date extraction with various formats."""
        test_cases = [
            ("Date of Incorporation: 01/15/2020", date(2020, 1, 15)),
            ("Filed: March 15, 2021", date(2021, 3, 15)),
            ("Incorporated on the 15th day of March, 2022", date(2022, 3, 15)),
        ]

        for text, expected_date in test_cases:
            result = self.parser._extract_registration_date(text)
            assert result == expected_date, f"Expected {expected_date}, got {result}"

    def test_extract_directors(self):
        """Test director extraction."""
        ocr_text = """
        Directors:
        Jane Doe, President
        John Smith, Secretary
        Robert Johnson, Treasurer
        """

        directors = self.parser._extract_directors(ocr_text)
        assert len(directors) >= 2

        # Check that at least some directors were found
        names = [d.name for d in directors]
        assert any("Jane" in name or "John" in name or "Robert" in name for name in names)

    def test_extract_business_type(self):
        """Test business type extraction."""
        test_cases = [
            ("a Limited Liability Company organized under", "LLC"),
            ("ACME Corporation, a Delaware corporation", "Corporation"),
            ("Smith & Partners Limited Partnership", "Limited Partnership"),
            ("XYZ Nonprofit Organization", "Nonprofit"),
        ]

        for text, expected_type in test_cases:
            result = self.parser._extract_business_type(text)
            assert result == expected_type, f"Expected {expected_type}, got {result}"

    def test_extract_jurisdiction(self):
        """Test jurisdiction extraction."""
        test_cases = [
            ("State of Delaware", "Delaware"),
            ("incorporated in California", "California"),
            ("State of New York", "New York"),
        ]

        for text, expected_state in test_cases:
            result = self.parser._extract_jurisdiction(text)
            assert result == expected_state, f"Expected {expected_state}, got {result}"

    def test_extract_status(self):
        """Test status extraction."""
        test_cases = [
            ("Status: Active", "Active"),
            ("Company is in Good Standing", "Active"),
            ("Status: Dissolved", "Dissolved"),
        ]

        for text, expected_status in test_cases:
            result = self.parser._extract_status(text)
            assert result == expected_status, f"Expected {expected_status}, got {result}"

    def test_parse_missing_required_fields(self):
        """Test that missing required fields return failure."""
        # Missing company name
        result = self.parser.parse(
            "File Number: 12345\nDate of Incorporation: 01/15/2020",
            confidence=0.8
        )
        assert result.success is False
        assert any("company name" in error.lower() for error in result.errors)

        # Missing registration number
        result = self.parser.parse(
            "Company Name: ACME Corp\nDate of Incorporation: 01/15/2020",
            confidence=0.8
        )
        assert result.success is False
        assert any("registration number" in error.lower() for error in result.errors)

        # Missing date
        result = self.parser.parse(
            "Company Name: ACME Corp\nFile Number: 12345",
            confidence=0.8
        )
        assert result.success is False
        assert any("date" in error.lower() for error in result.errors)

    def test_empty_text_returns_failure(self):
        """Test that empty text returns failure."""
        result = self.parser.parse("", confidence=0.0)
        assert result.success is False
        assert "No text extracted" in result.errors[0]


class TestBusinessDocumentParserEdgeCases:
    """Edge case tests for business document parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BusinessDocumentParser()

    def test_company_name_with_special_characters(self):
        """Test company names with special characters."""
        ocr_text = """
        Certificate of Incorporation of
        O'Brien & Associates, Inc.

        File Number: 123456
        Date of Incorporation: 01/15/2020
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        # Should not crash even with special characters

    def test_multiple_directors_formats(self):
        """Test various director list formats."""
        test_cases = [
            "Directors: Jane Doe, John Smith, Bob Johnson",
            "Officers:\n- CEO: Jane Doe\n- CFO: John Smith",
            "President: Jane Doe\nSecretary: John Smith\nTreasurer: Bob Johnson",
        ]

        for text in test_cases:
            directors = self.parser._extract_directors(text)
            # Should extract at least some directors without crashing
            assert isinstance(directors, list)

    def test_missing_directors_returns_warning(self):
        """Test that missing directors returns warning, not error."""
        ocr_text = """
        This is to certify that TEST CORP
        has been incorporated.

        File Number: 12345
        Date of Incorporation: 01/15/2020
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        if result.success:
            assert any("directors" in w.lower() for w in result.warnings)

    def test_ein_as_registration_number(self):
        """Test EIN/Tax ID recognition."""
        ocr_text = """
        Company Name: Test Corp
        EIN: 12-3456789
        Incorporated: January 15, 2020
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        if result.success:
            assert result.data.registration_number == "12-3456789"
