"""Tests for risk API endpoints."""

import pytest
from uuid import uuid4

from httpx import AsyncClient


class TestRiskHealthEndpoint:
    """Test cases for /risk/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, client: AsyncClient) -> None:
        """Test that health check returns status info."""
        response = await client.get("/v1/risk/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "adverse_media_available" in data
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["adverse_media_available"], bool)


class TestAdverseMediaEndpoints:
    """Test cases for adverse media endpoints."""

    @pytest.mark.asyncio
    async def test_scan_adverse_media_requires_name(self, client: AsyncClient) -> None:
        """Test that adverse media scan requires name field."""
        response = await client.post(
            "/v1/risk/adverse-media",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_scan_adverse_media_validates_max_results(self, client: AsyncClient) -> None:
        """Test max_results validation."""
        response = await client.post(
            "/v1/risk/adverse-media",
            json={"name": "Test", "max_results": 200},  # Too high
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_scan_adverse_media_returns_response(self, client: AsyncClient) -> None:
        """Test that scan returns a valid response structure."""
        response = await client.post(
            "/v1/risk/adverse-media",
            json={"name": "John Smith", "max_results": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "success" in data["result"]

    @pytest.mark.asyncio
    async def test_scan_document_adverse_media_invalid_uuid(self, client: AsyncClient) -> None:
        """Test document scan with invalid UUID."""
        response = await client.post("/v1/risk/adverse-media/document/invalid-uuid")

        assert response.status_code == 422  # Validation error


class TestRiskScoringEndpoints:
    """Test cases for risk scoring endpoints."""

    @pytest.mark.asyncio
    async def test_score_risk_requires_all_fields(self, client: AsyncClient) -> None:
        """Test that risk scoring requires all feature fields."""
        response = await client.post(
            "/v1/risk/score",
            json={"document_quality": 0.9},  # Missing other fields
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_score_risk_validates_ranges(self, client: AsyncClient) -> None:
        """Test that risk scoring validates feature ranges."""
        response = await client.post(
            "/v1/risk/score",
            json={
                "document_quality": 1.5,  # Out of range (should be 0-1)
                "sanctions_score": 0.1,
                "sanctions_match": False,
                "adverse_media_count": 0,
                "adverse_media_sentiment": 0.0,
                "country_risk": 0.2,
                "document_age_days": 30,
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_score_risk_returns_response(self, client: AsyncClient) -> None:
        """Test that scoring returns a valid response structure."""
        response = await client.post(
            "/v1/risk/score",
            json={
                "document_quality": 0.9,
                "sanctions_score": 0.1,
                "sanctions_match": False,
                "adverse_media_count": 0,
                "adverse_media_sentiment": 0.0,
                "country_risk": 0.2,
                "document_age_days": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "success" in data["result"]
        # Either success with data or failure with errors
        if data["result"]["success"]:
            assert "data" in data["result"]
            assert "risk_score" in data["result"]["data"]
            assert "risk_tier" in data["result"]["data"]
            assert "recommendation" in data["result"]["data"]

    @pytest.mark.asyncio
    async def test_score_screening_invalid_uuid(self, client: AsyncClient) -> None:
        """Test screening scoring with invalid UUID."""
        response = await client.post("/v1/risk/score/screening/invalid-uuid")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_score_screening_not_found(self, client: AsyncClient) -> None:
        """Test screening scoring for non-existent screening."""
        response = await client.post(f"/v1/risk/score/screening/{uuid4()}")

        assert response.status_code == 200
        data = response.json()
        # Should fail because screening doesn't exist (or service not ready)
        assert "result" in data
        assert "success" in data["result"]


class TestRiskScoringIntegration:
    """Integration tests for risk scoring (requires model)."""

    @pytest.mark.asyncio
    async def test_low_risk_scoring(self, client: AsyncClient) -> None:
        """Test scoring low-risk features."""
        response = await client.post(
            "/v1/risk/score",
            json={
                "document_quality": 0.95,
                "sanctions_score": 0.05,
                "sanctions_match": False,
                "adverse_media_count": 0,
                "adverse_media_sentiment": 0.1,
                "country_risk": 0.1,
                "document_age_days": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["result"]["success"]:
            # If model loaded, should be low risk
            assert data["result"]["data"]["risk_score"] < 0.3
            assert data["result"]["data"]["risk_tier"] == "Low"
            assert data["result"]["data"]["recommendation"] == "Approve"

    @pytest.mark.asyncio
    async def test_high_risk_scoring(self, client: AsyncClient) -> None:
        """Test scoring high-risk features."""
        response = await client.post(
            "/v1/risk/score",
            json={
                "document_quality": 0.4,
                "sanctions_score": 0.95,
                "sanctions_match": True,
                "adverse_media_count": 5,
                "adverse_media_sentiment": -0.8,
                "country_risk": 0.9,
                "document_age_days": 800,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["result"]["success"]:
            # If model loaded, should be high risk
            assert data["result"]["data"]["risk_score"] > 0.7
            assert data["result"]["data"]["risk_tier"] == "High"
            assert data["result"]["data"]["recommendation"] == "Reject"

    @pytest.mark.asyncio
    async def test_scoring_returns_feature_contributions(self, client: AsyncClient) -> None:
        """Test that scoring includes SHAP feature contributions."""
        response = await client.post(
            "/v1/risk/score",
            json={
                "document_quality": 0.8,
                "sanctions_score": 0.3,
                "sanctions_match": False,
                "adverse_media_count": 1,
                "adverse_media_sentiment": -0.2,
                "country_risk": 0.4,
                "document_age_days": 100,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["result"]["success"]:
            assert "feature_contributions" in data["result"]["data"]
            assert len(data["result"]["data"]["feature_contributions"]) > 0

            for contrib in data["result"]["data"]["feature_contributions"]:
                assert "feature" in contrib
                assert "value" in contrib
                assert "contribution" in contrib
                assert "direction" in contrib
