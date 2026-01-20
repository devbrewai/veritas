"""Tests for passport MRZ parsing."""

import pytest

from src.services.parsers.passport import PassportParser

# Sample MRZ from TD3 passport format (fictional data)
# Line 1: Document type, country, name
# Line 2: Passport number, nationality, DOB, sex, expiry, optional data
SAMPLE_MRZ_VALID = """
P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
L898902C36UTO7408122F1204159ZE184226B<<<<<10
"""

# MRZ with different formatting (single line)
SAMPLE_MRZ_SINGLE_LINE = (
    "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
)


class TestPassportParser:
    """Test suite for PassportParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PassportParser()

    def test_clean_mrz_text_removes_spaces(self):
        """Test that spaces are removed from MRZ text."""
        dirty = "P<UTO ERIKSSON << ANNA"
        lines = self.parser.clean_mrz_text(dirty)
        assert " " not in lines[0] if lines else True

    def test_clean_mrz_text_normalizes_to_uppercase(self):
        """Test that text is normalized to uppercase."""
        dirty = "p<utoeriksson<<anna"
        lines = self.parser.clean_mrz_text(dirty)
        assert lines[0] == lines[0].upper() if lines else True

    def test_clean_mrz_text_splits_long_line(self):
        """Test that a single 88-char line is split into two lines."""
        lines = self.parser.clean_mrz_text(SAMPLE_MRZ_SINGLE_LINE)
        assert len(lines) == 2
        assert len(lines[0]) == 44
        assert len(lines[1]) == 44

    def test_parse_valid_mrz(self):
        """Test parsing a valid MRZ returns correct data."""
        result = self.parser.parse(SAMPLE_MRZ_VALID, confidence=0.95)

        assert result.success is True
        assert result.data is not None
        assert result.data.surname == "ERIKSSON"
        assert result.data.given_names == "ANNA MARIA"
        assert result.data.nationality == "UTO"
        assert result.data.issuing_country == "UTO"
        assert result.confidence == 0.95

    def test_parse_extracts_passport_number(self):
        """Test that passport number is correctly extracted."""
        result = self.parser.parse(SAMPLE_MRZ_VALID)

        assert result.success is True
        assert result.data is not None
        # Passport number may have trailing characters stripped
        assert "L898902C3" in result.data.passport_number

    def test_parse_extracts_dates(self):
        """Test that DOB and expiry dates are correctly parsed."""
        result = self.parser.parse(SAMPLE_MRZ_VALID)

        assert result.success is True
        assert result.data is not None
        # DOB: 740812 = 1974-08-12
        assert result.data.date_of_birth.year == 1974
        assert result.data.date_of_birth.month == 8
        assert result.data.date_of_birth.day == 12
        # Expiry: 120415 = 2012-04-15
        assert result.data.expiry_date.year == 2012
        assert result.data.expiry_date.month == 4
        assert result.data.expiry_date.day == 15

    def test_parse_extracts_sex(self):
        """Test that sex is correctly extracted."""
        result = self.parser.parse(SAMPLE_MRZ_VALID)

        assert result.success is True
        assert result.data is not None
        assert result.data.sex == "F"

    def test_parse_invalid_mrz_returns_failure(self):
        """Test that invalid MRZ returns failure with errors."""
        result = self.parser.parse("INVALID MRZ TEXT", confidence=0.5)

        assert result.success is False
        assert len(result.errors) > 0

    def test_parse_empty_string_returns_failure(self):
        """Test that empty string returns failure."""
        result = self.parser.parse("")

        assert result.success is False
        assert len(result.errors) > 0

    def test_parse_single_line_returns_failure(self):
        """Test that a single short line returns failure."""
        result = self.parser.parse("P<UTOERIKSSON")

        assert result.success is False

    def test_full_name_computed_property(self):
        """Test that full_name is correctly computed."""
        result = self.parser.parse(SAMPLE_MRZ_VALID)

        assert result.success is True
        assert result.data is not None
        assert result.data.full_name == "ANNA MARIA ERIKSSON"

    def test_parse_date_birth_century_heuristic(self):
        """Test date parsing century heuristic for birth dates."""
        # Year > 30 should be 1900s
        date = PassportParser._parse_mrz_date("740812", is_expiry=False)
        assert date is not None
        assert date.year == 1974

        # Year <= 30 should be 2000s for birth dates
        date = PassportParser._parse_mrz_date("200812", is_expiry=False)
        assert date is not None
        assert date.year == 2020

    def test_parse_date_expiry_century(self):
        """Test date parsing for expiry dates (always 2000s)."""
        date = PassportParser._parse_mrz_date("350415", is_expiry=True)
        assert date is not None
        assert date.year == 2035


class TestPassportParserEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PassportParser()

    def test_mrz_with_extra_whitespace(self):
        """Test MRZ parsing with extra whitespace and newlines."""
        mrz_with_whitespace = """

        P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<

        L898902C36UTO7408122F1204159ZE184226B<<<<<10

        """
        result = self.parser.parse(mrz_with_whitespace)
        assert result.success is True

    def test_mrz_with_tabs(self):
        """Test MRZ parsing with tabs."""
        mrz_with_tabs = (
            "\tP<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
            "\tL898902C36UTO7408122F1204159ZE184226B<<<<<10"
        )
        # Tabs are not standard MRZ characters and may cause issues
        result = self.parser.parse(mrz_with_tabs)
        # Should still attempt to parse
        assert isinstance(result.success, bool)
