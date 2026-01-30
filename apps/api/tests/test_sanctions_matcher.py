"""
Unit tests for sanctions fuzzy matching engine.
"""

import numpy as np
import pandas as pd
import pytest

from src.services.sanctions.matcher import (
    IS_MATCH_THRESHOLD,
    REVIEW_THRESHOLD,
    SanctionsMatcher,
    SanctionsMatch,
    SanctionsQuery,
    SanctionsResponse,
    apply_decision_threshold,
    composite_score_batch,
    compute_similarity_batch,
    get_candidates,
    get_first_token,
    get_initials_signature,
    get_token_count_bucket,
)


class TestDecisionThresholds:
    """Tests for decision threshold constants and function."""

    def test_match_threshold_value(self):
        """Match threshold should be 0.90."""
        assert IS_MATCH_THRESHOLD == 0.90

    def test_review_threshold_value(self):
        """Review threshold should be 0.80."""
        assert REVIEW_THRESHOLD == 0.80

    def test_apply_threshold_match(self):
        """Score >= 0.90 should return match."""
        is_match, decision = apply_decision_threshold(0.95)
        assert is_match is True
        assert decision == "match"

        is_match, decision = apply_decision_threshold(0.90)
        assert is_match is True
        assert decision == "match"

    def test_apply_threshold_review(self):
        """Score >= 0.80 and < 0.90 should return review."""
        is_match, decision = apply_decision_threshold(0.85)
        assert is_match is False
        assert decision == "review"

        is_match, decision = apply_decision_threshold(0.80)
        assert is_match is False
        assert decision == "review"

    def test_apply_threshold_no_match(self):
        """Score < 0.80 should return no_match."""
        is_match, decision = apply_decision_threshold(0.79)
        assert is_match is False
        assert decision == "no_match"

        is_match, decision = apply_decision_threshold(0.50)
        assert is_match is False
        assert decision == "no_match"

        is_match, decision = apply_decision_threshold(0.0)
        assert is_match is False
        assert decision == "no_match"

    def test_apply_threshold_boundary(self):
        """Test exact boundary values."""
        # Just below review threshold
        is_match, decision = apply_decision_threshold(0.7999)
        assert decision == "no_match"

        # Exactly at review threshold
        is_match, decision = apply_decision_threshold(0.80)
        assert decision == "review"

        # Just below match threshold
        is_match, decision = apply_decision_threshold(0.8999)
        assert decision == "review"


class TestBlockingFunctions:
    """Tests for blocking helper functions."""

    def test_get_first_token(self):
        """Should return first token or None."""
        assert get_first_token(["john", "doe"]) == "john"
        assert get_first_token(["vladimir"]) == "vladimir"
        assert get_first_token([]) is None

    def test_get_token_count_bucket_single(self):
        """Single token should return 'single'."""
        assert get_token_count_bucket(["john"]) == "single"

    def test_get_token_count_bucket_double(self):
        """Two tokens should return 'double'."""
        assert get_token_count_bucket(["john", "doe"]) == "double"

    def test_get_token_count_bucket_medium(self):
        """Three or four tokens should return 'medium'."""
        assert get_token_count_bucket(["john", "doe", "smith"]) == "medium"
        assert get_token_count_bucket(["a", "b", "c", "d"]) == "medium"

    def test_get_token_count_bucket_long(self):
        """Five or more tokens should return 'long'."""
        assert get_token_count_bucket(["a", "b", "c", "d", "e"]) == "long"
        assert get_token_count_bucket(["a", "b", "c", "d", "e", "f"]) == "long"

    def test_get_initials_signature(self):
        """Should generate hyphen-separated initials."""
        assert get_initials_signature(["john", "doe"]) == "j-d"
        assert get_initials_signature(["vladimir", "putin"]) == "v-p"
        assert get_initials_signature(["kim", "jong", "un"]) == "k-j-u"

    def test_get_initials_signature_empty(self):
        """Empty tokens should return empty string."""
        assert get_initials_signature([]) == ""


class TestGetCandidates:
    """Tests for candidate retrieval function."""

    @pytest.fixture
    def sample_indices(self):
        """Create sample blocking indices."""
        return {
            "first_token": {
                "john": [0, 1, 2],
                "jane": [3, 4],
                "vladimir": [5],
            },
            "bucket": {
                "double": [0, 1, 2, 3, 4, 5],
                "single": [6, 7],
            },
            "initials": {
                "j-d": [0, 1],
                "j-s": [2, 3],
                "v-p": [5],
            },
        }

    def test_candidates_prioritized_by_strategy_count(self, sample_indices):
        """Candidates matching multiple strategies should have higher priority."""
        candidate_indices, priority_scores = get_candidates(
            ["john", "doe"],
            sample_indices["first_token"],
            sample_indices["bucket"],
            sample_indices["initials"],
        )

        # Index 0 and 1 match first_token (john) and initials (j-d) and bucket
        # They should have priority 3 + 2 + 1 = 6
        assert 0 in candidate_indices
        assert 1 in candidate_indices
        assert priority_scores[0] == 6  # first_token(3) + initials(2) + bucket(1)
        assert priority_scores[1] == 6

    def test_candidates_sorted_by_priority(self, sample_indices):
        """Candidates should be sorted by priority descending."""
        candidate_indices, priority_scores = get_candidates(
            ["john", "doe"],
            sample_indices["first_token"],
            sample_indices["bucket"],
            sample_indices["initials"],
        )

        # First candidates should have highest priority
        if len(candidate_indices) > 1:
            first_priority = priority_scores[candidate_indices[0]]
            second_priority = priority_scores[candidate_indices[1]]
            assert first_priority >= second_priority

    def test_candidates_empty_tokens(self, sample_indices):
        """Empty tokens should return empty candidates."""
        candidate_indices, _ = get_candidates(
            [],
            sample_indices["first_token"],
            sample_indices["bucket"],
            sample_indices["initials"],
        )
        assert len(candidate_indices) == 0


class TestScoringFunctions:
    """Tests for similarity scoring functions."""

    def test_compute_similarity_batch_returns_arrays(self):
        """Should return three numpy arrays."""
        query = "john doe"
        candidates = ["john doe", "jane doe", "john smith"]

        set_scores, sort_scores, partial_scores = compute_similarity_batch(
            query, candidates
        )

        assert isinstance(set_scores, np.ndarray)
        assert isinstance(sort_scores, np.ndarray)
        assert isinstance(partial_scores, np.ndarray)
        assert len(set_scores) == 3
        assert len(sort_scores) == 3
        assert len(partial_scores) == 3

    def test_compute_similarity_exact_match(self):
        """Exact match should return high scores."""
        set_scores, sort_scores, partial_scores = compute_similarity_batch(
            "john doe", ["john doe"]
        )

        assert set_scores[0] == pytest.approx(1.0)
        assert sort_scores[0] == pytest.approx(1.0)
        assert partial_scores[0] == pytest.approx(1.0)

    def test_compute_similarity_empty_candidates(self):
        """Empty candidates should return empty arrays."""
        set_scores, sort_scores, partial_scores = compute_similarity_batch(
            "john doe", []
        )

        assert len(set_scores) == 0
        assert len(sort_scores) == 0
        assert len(partial_scores) == 0

    def test_composite_score_weights(self):
        """Composite score should use 40/40/20 weights."""
        set_scores = np.array([1.0])
        sort_scores = np.array([1.0])
        partial_scores = np.array([1.0])

        composite = composite_score_batch(set_scores, sort_scores, partial_scores)
        assert composite[0] == pytest.approx(1.0)

        # Test with different values
        set_scores = np.array([1.0])
        sort_scores = np.array([0.0])
        partial_scores = np.array([0.0])

        composite = composite_score_batch(set_scores, sort_scores, partial_scores)
        assert composite[0] == pytest.approx(0.4)  # Only set_score contributes 40%

    def test_composite_score_batch(self):
        """Should compute weighted average correctly."""
        set_scores = np.array([0.8, 0.9])
        sort_scores = np.array([0.7, 0.85])
        partial_scores = np.array([0.6, 0.8])

        composite = composite_score_batch(set_scores, sort_scores, partial_scores)

        expected_0 = 0.4 * 0.8 + 0.4 * 0.7 + 0.2 * 0.6  # 0.72
        expected_1 = 0.4 * 0.9 + 0.4 * 0.85 + 0.2 * 0.8  # 0.86

        assert composite[0] == pytest.approx(expected_0)
        assert composite[1] == pytest.approx(expected_1)


class TestSanctionsQuery:
    """Tests for SanctionsQuery dataclass."""

    def test_valid_query(self):
        """Should create valid query."""
        query = SanctionsQuery(name="John Doe")
        assert query.name == "John Doe"
        assert query.country is None
        assert query.program is None
        assert query.top_k == 3

    def test_query_with_options(self):
        """Should accept optional parameters."""
        query = SanctionsQuery(
            name="John Doe",
            country="US",
            program="IRAN",
            top_k=5,
        )
        assert query.country == "US"
        assert query.program == "IRAN"
        assert query.top_k == 5

    def test_empty_name_raises(self):
        """Should raise ValueError for empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            SanctionsQuery(name="")

        with pytest.raises(ValueError, match="name cannot be empty"):
            SanctionsQuery(name="   ")

    def test_invalid_top_k_raises(self):
        """Should raise ValueError for invalid top_k."""
        with pytest.raises(ValueError, match="top_k must be between 1 and 10"):
            SanctionsQuery(name="John", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 10"):
            SanctionsQuery(name="John", top_k=11)


class TestSanctionsMatch:
    """Tests for SanctionsMatch dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        match = SanctionsMatch(
            matched_name="John Doe",
            score=0.95,
            is_match=True,
            decision="match",
            country="US",
            program="IRAN",
            source="SDN",
            uid="12345",
            sim_set=0.96,
            sim_sort=0.94,
            sim_partial=0.92,
        )

        d = match.to_dict()

        assert d["matched_name"] == "John Doe"
        assert d["score"] == 0.95
        assert d["is_match"] is True
        assert d["decision"] == "match"
        assert d["country"] == "US"
        assert d["sim_set"] == 0.96


class TestSanctionsResponse:
    """Tests for SanctionsResponse dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        response = SanctionsResponse(
            query="John Doe",
            top_matches=[],
            applied_filters={"country": None, "program": None},
            latency_ms=10.5,
            version="1.0.0",
        )

        d = response.to_dict()

        assert d["query"] == "John Doe"
        assert d["top_matches"] == []
        assert d["latency_ms"] == 10.5
        assert d["version"] == "1.0.0"
        assert "timestamp" in d


class TestSanctionsMatcher:
    """Tests for SanctionsMatcher class."""

    @pytest.fixture
    def sample_matcher(self):
        """Create a matcher with sample data."""
        # Create sample sanctions index
        data = {
            "uid": ["1", "2", "3", "4", "5"],
            "name": [
                "John Doe",
                "Jane Doe",
                "John Smith",
                "Vladimir Putin",
                "Kim Jong Un",
            ],
            "name_norm": [
                "john doe",
                "jane doe",
                "john smith",
                "vladimir putin",
                "kim jong un",
            ],
            "country": ["US", "US", "UK", "RU", "KP"],
            "program": ["IRAN", "CUBA", "IRAN", "UKRAINE-EO13661", "DPRK"],
            "source": ["SDN", "SDN", "SDN", "SDN", "SDN"],
        }
        df = pd.DataFrame(data)

        # Build indices
        first_token_index = {
            "john": [0, 2],
            "jane": [1],
            "vladimir": [3],
            "kim": [4],
        }
        bucket_index = {
            "double": [0, 1, 2, 3],
            "medium": [4],
        }
        initials_index = {
            "j-d": [0, 1],
            "j-s": [2],
            "v-p": [3],
            "k-j-u": [4],
        }

        return SanctionsMatcher(
            sanctions_index=df,
            first_token_index=first_token_index,
            bucket_index=bucket_index,
            initials_index=initials_index,
            version="1.0.0-test",
        )

    def test_match_exact_name(self, sample_matcher):
        """Exact name should return high score match."""
        query = SanctionsQuery(name="John Doe")
        response = sample_matcher.match(query)

        assert len(response.top_matches) > 0
        assert response.top_matches[0].matched_name == "John Doe"
        assert response.top_matches[0].score >= 0.90
        assert response.top_matches[0].is_match is True

    def test_match_similar_name(self, sample_matcher):
        """Similar name should return matches."""
        query = SanctionsQuery(name="Jon Doe")  # Typo
        response = sample_matcher.match(query)

        assert len(response.top_matches) > 0
        # Should still find John Doe as a match
        names = [m.matched_name for m in response.top_matches]
        assert any("Doe" in name for name in names)

    def test_match_no_results(self, sample_matcher):
        """Unrelated name should return no matches."""
        query = SanctionsQuery(name="Xyz Abc")
        response = sample_matcher.match(query)

        # Should return response but with low-scoring or no matches
        assert response.query == "Xyz Abc"
        assert response.version == "1.0.0-test"

    def test_match_with_country_filter(self, sample_matcher):
        """Country filter should restrict results."""
        query = SanctionsQuery(name="John", country="UK")
        response = sample_matcher.match(query)

        # Only UK matches should be returned
        for match in response.top_matches:
            assert match.country == "UK"

    def test_match_with_program_filter(self, sample_matcher):
        """Program filter should restrict results."""
        query = SanctionsQuery(name="John", program="IRAN")
        response = sample_matcher.match(query)

        # Only IRAN program matches should be returned
        for match in response.top_matches:
            assert "IRAN" in (match.program or "").upper()

    def test_match_returns_response_metadata(self, sample_matcher):
        """Should include latency and version metadata."""
        query = SanctionsQuery(name="John Doe")
        response = sample_matcher.match(query)

        assert response.latency_ms >= 0
        assert response.version == "1.0.0-test"
        assert response.timestamp is not None
        assert response.applied_filters == {"country": None, "program": None}

    def test_match_top_k_limit(self, sample_matcher):
        """Should respect top_k limit."""
        query = SanctionsQuery(name="John", top_k=2)
        response = sample_matcher.match(query)

        assert len(response.top_matches) <= 2

    def test_match_empty_tokens(self, sample_matcher):
        """Query that normalizes to empty should return no matches."""
        query = SanctionsQuery(name="中国")  # Non-Latin only
        response = sample_matcher.match(query)

        assert len(response.top_matches) == 0
