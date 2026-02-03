"""Tests for JWKS service."""

import pytest
from unittest.mock import MagicMock, patch

from src.services.auth.jwks import JWKSService, jwks_service


class TestJWKSService:
    """Tests for JWKSService."""

    def test_default_jwks_url(self):
        """Test that default JWKS URL is constructed from settings."""
        with patch("src.services.auth.jwks.get_settings") as mock_settings:
            mock_settings.return_value.BETTER_AUTH_URL = "http://localhost:3000"
            mock_settings.return_value.JWKS_CACHE_TTL = 3600

            service = JWKSService()
            assert service.jwks_url == "http://localhost:3000/api/auth/jwks"

    def test_custom_jwks_url(self):
        """Test that custom JWKS URL can be provided."""
        with patch("src.services.auth.jwks.get_settings") as mock_settings:
            mock_settings.return_value.JWKS_CACHE_TTL = 3600

            service = JWKSService(jwks_url="http://custom.example.com/jwks")
            assert service.jwks_url == "http://custom.example.com/jwks"

    def test_custom_cache_ttl(self):
        """Test that custom cache TTL can be provided."""
        with patch("src.services.auth.jwks.get_settings") as mock_settings:
            mock_settings.return_value.BETTER_AUTH_URL = "http://localhost:3000"
            mock_settings.return_value.JWKS_CACHE_TTL = 3600

            service = JWKSService(cache_ttl=7200)
            assert service._cache_ttl == 7200

    def test_clear_cache(self):
        """Test that cache can be cleared."""
        with patch("src.services.auth.jwks.get_settings") as mock_settings:
            mock_settings.return_value.BETTER_AUTH_URL = "http://localhost:3000"
            mock_settings.return_value.JWKS_CACHE_TTL = 3600

            service = JWKSService()
            # Simulate having a client
            service._client = MagicMock()
            service._cache["test"] = "value"

            service.clear_cache()

            assert service._client is None
            assert len(service._cache) == 0

    def test_get_signing_key_creates_client(self):
        """Test that get_signing_key creates PyJWKClient on first call."""
        with patch("src.services.auth.jwks.get_settings") as mock_settings:
            mock_settings.return_value.BETTER_AUTH_URL = "http://localhost:3000"
            mock_settings.return_value.JWKS_CACHE_TTL = 3600

            with patch("src.services.auth.jwks.PyJWKClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                service = JWKSService()
                assert service._client is None

                # This would normally fail without a real token,
                # but we're testing that the client gets created
                service._get_client()

                assert service._client is not None
                mock_client_class.assert_called_once()


class TestJWKSSingleton:
    """Tests for the JWKS singleton instance."""

    def test_singleton_exists(self):
        """Test that the singleton instance exists."""
        assert jwks_service is not None

    def test_singleton_is_jwks_service(self):
        """Test that the singleton is a JWKSService instance."""
        assert isinstance(jwks_service, JWKSService)
