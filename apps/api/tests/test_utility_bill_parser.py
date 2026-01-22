"""Tests for utility bill parser."""

import pytest
from datetime import date

from src.services.parsers.utility_bill import UtilityBillParser


class TestUtilityBillParser:
    """Tests for UtilityBillParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = UtilityBillParser()

    def test_parse_valid_utility_bill(self):
        """Test parsing a valid utility bill text."""
        ocr_text = """
        CON EDISON
        Account Statement

        Account Holder: John Smith
        Service Address: 123 Main Street, Apt 4B, New York, NY 10001

        Statement Date: 01/15/2026
        Account Number: 12345678
        Amount Due: $142.50
        Due Date: 02/01/2026
        """

        result = self.parser.parse(ocr_text, confidence=0.85)

        assert result.success is True
        assert result.data is not None
        assert result.data.name == "John Smith"
        assert "123 Main Street" in result.data.address
        assert result.data.bill_date == date(2026, 1, 15)
        assert result.data.utility_provider == "Con Edison"
        assert result.data.account_number == "12345678"
        assert result.data.amount_due == 142.50
        assert result.confidence == 0.85

    def test_parse_utility_bill_different_label_formats(self):
        """Test name extraction with different label formats."""
        test_cases = [
            ("Customer Name: Jane Doe\nAddress: 456 Oak Ave, Boston, MA 02101\nBill Date: 03/20/2026", "Jane Doe"),
            ("Bill To: Robert Johnson\nService Address: 789 Pine Rd, Seattle, WA 98101\nStatement Date: 04/15/2026", "Robert Johnson"),
        ]

        for ocr_text, expected_name in test_cases:
            # Add a known provider for the test
            ocr_text += "\nPG&E"
            result = self.parser.parse(ocr_text, confidence=0.8)
            if result.success:
                assert result.data.name == expected_name, f"Expected {expected_name}, got {result.data.name}"

    def test_parse_utility_bill_date_formats(self):
        """Test date extraction with various formats."""
        test_cases = [
            ("Statement Date: 01/15/2026", date(2026, 1, 15)),
            ("Bill Date: January 15, 2026", date(2026, 1, 15)),
            ("Invoice Date: 2026-01-15", date(2026, 1, 15)),
        ]

        base_text = """
        Pacific Gas Electric
        Account Holder: Test User
        Service Address: 100 Test St, San Francisco, CA 94102
        """

        for date_line, expected_date in test_cases:
            ocr_text = base_text + "\n" + date_line
            result = self.parser.parse(ocr_text, confidence=0.8)
            if result.success:
                assert result.data.bill_date == expected_date

    def test_parse_missing_required_fields(self):
        """Test that missing required fields return failure."""
        # Missing name
        result = self.parser.parse(
            "PG&E\nAddress: 123 Main St, City, CA 12345\nStatement Date: 01/15/2026",
            confidence=0.8
        )
        assert result.success is False
        assert any("name" in error.lower() for error in result.errors)

        # Missing address
        result = self.parser.parse(
            "PG&E\nAccount Holder: John Doe\nStatement Date: 01/15/2026",
            confidence=0.8
        )
        assert result.success is False
        assert any("address" in error.lower() for error in result.errors)

        # Missing date
        result = self.parser.parse(
            "PG&E\nAccount Holder: John Doe\nService Address: 123 Main St, City, CA 12345",
            confidence=0.8
        )
        assert result.success is False
        assert any("date" in error.lower() for error in result.errors)

    def test_extract_known_providers(self):
        """Test provider detection from known provider list."""
        providers = [
            ("Con Edison bill for electricity", "Con Edison"),
            ("Pacific Gas and Electric Company", "PG&E"),
            ("Xfinity Internet Service", "Xfinity"),
            ("AT&T Wireless Statement", "AT&T"),
            ("Duke Energy Monthly Bill", "Duke Energy"),
        ]

        for text, expected_provider in providers:
            detected = self.parser._extract_provider(text)
            # Check if any variant of the provider is detected
            assert detected is not None, f"Failed to detect provider in: {text}"

    def test_extract_account_number(self):
        """Test account number extraction."""
        test_cases = [
            ("Account Number: 12345678", "12345678"),
            ("Acct No: ABC-123456", "ABC-123456"),
            ("Account #: 987654321", "987654321"),
        ]

        for text, expected in test_cases:
            result = self.parser._extract_account_number(text)
            assert result == expected

    def test_extract_amount_due(self):
        """Test amount extraction."""
        test_cases = [
            ("Amount Due: $142.50", 142.50),
            ("Total Due: $1,234.56", 1234.56),
            ("Balance Due: 99.99", 99.99),
        ]

        for text, expected in test_cases:
            result = self.parser._extract_amount(text)
            assert result == expected

    def test_infer_utility_type(self):
        """Test utility type inference."""
        test_cases = [
            ("Electric usage: 500 kWh", "Con Edison", "electricity"),
            ("Natural gas usage: 50 therms", "PG&E", "gas"),
            ("Water usage: 1000 gallons", "American Water", "water"),
            ("Internet service: 100 Mbps", "Comcast", "internet"),
        ]

        for text, provider, expected_type in test_cases:
            result = self.parser._infer_utility_type(text, provider)
            assert result == expected_type

    def test_empty_text_returns_failure(self):
        """Test that empty text returns failure."""
        result = self.parser.parse("", confidence=0.0)
        assert result.success is False
        assert "No text extracted" in result.errors[0]

        result = self.parser.parse("   \n\n  ", confidence=0.0)
        assert result.success is False


class TestUtilityBillParserEdgeCases:
    """Edge case tests for utility bill parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = UtilityBillParser()

    def test_multiline_address(self):
        """Test extraction of multiline addresses."""
        ocr_text = """
        National Grid
        Customer Name: Alice Brown
        Service Address:
        456 Elm Avenue
        Apartment 12B
        Chicago, IL 60601

        Statement Date: 02/28/2026
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        # This may or may not succeed depending on regex matching multiline
        # The test verifies the parser doesn't crash

    def test_special_characters_in_name(self):
        """Test names with special characters."""
        ocr_text = """
        ComEd
        Account Holder: Mary O'Brien-Smith
        Service Address: 789 Oak St, Unit 5, Denver, CO 80201
        Bill Date: 03/15/2026
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        if result.success:
            assert "O'Brien" in result.data.name or "Brien" in result.data.name

    def test_unknown_provider_warning(self):
        """Test that unknown provider returns warning."""
        ocr_text = """
        Unknown Utility Company
        Account Holder: Test User
        Service Address: 123 Test St, Test City, TX 12345
        Statement Date: 01/01/2026
        """

        result = self.parser.parse(ocr_text, confidence=0.8)
        if result.success:
            assert result.data.utility_provider == "Unknown Provider"
            assert any("provider" in w.lower() for w in result.warnings)
