"""Tests for token validation service."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID

from src.services.auth.tokens import TokenService, TokenValidationError, token_service


class TestTokenService:
    """Tests for TokenService."""

    def test_decode_token_success(self):
        """Test successful token decoding."""
        mock_payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "email": "test@example.com",
            "iat": 1234567890,
            "exp": 9999999999,
        }

        with patch("src.services.auth.tokens.jwks_service") as mock_jwks:
            with patch("src.services.auth.tokens.jwt.decode") as mock_decode:
                mock_signing_key = MagicMock()
                mock_signing_key.key = "test_key"
                mock_jwks.get_signing_key.return_value = mock_signing_key
                mock_decode.return_value = mock_payload

                service = TokenService()
                result = service.decode_token("test_token")

                assert result == mock_payload
                mock_jwks.get_signing_key.assert_called_once_with("test_token")
                mock_decode.assert_called_once()

    def test_decode_token_invalid(self):
        """Test decoding invalid token raises error."""
        with patch("src.services.auth.tokens.jwks_service") as mock_jwks:
            with patch("src.services.auth.tokens.jwt.decode") as mock_decode:
                from jwt.exceptions import InvalidTokenError

                mock_signing_key = MagicMock()
                mock_signing_key.key = "test_key"
                mock_jwks.get_signing_key.return_value = mock_signing_key
                mock_decode.side_effect = InvalidTokenError("Invalid token")

                service = TokenService()
                with pytest.raises(TokenValidationError) as exc:
                    service.decode_token("invalid_token")

                assert "Invalid token" in str(exc.value)

    def test_decode_token_jwks_error(self):
        """Test JWKS fetch error raises TokenValidationError."""
        with patch("src.services.auth.tokens.jwks_service") as mock_jwks:
            from jwt.exceptions import PyJWKClientError

            mock_jwks.get_signing_key.side_effect = PyJWKClientError("Cannot fetch JWKS")

            service = TokenService()
            with pytest.raises(TokenValidationError) as exc:
                service.decode_token("test_token")

            assert "signing key" in str(exc.value).lower()

    def test_get_user_id_success(self):
        """Test successful user ID extraction."""
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_payload = {"sub": user_id}

        with patch.object(TokenService, "decode_token", return_value=mock_payload):
            service = TokenService()
            result = service.get_user_id("test_token")

            assert result == UUID(user_id)

    def test_get_user_id_missing(self):
        """Test missing user ID raises error."""
        mock_payload = {"email": "test@example.com"}  # No 'sub' claim

        with patch.object(TokenService, "decode_token", return_value=mock_payload):
            service = TokenService()
            with pytest.raises(TokenValidationError) as exc:
                service.get_user_id("test_token")

            assert "missing user id" in str(exc.value).lower()

    def test_get_user_id_invalid_format(self):
        """Test invalid user ID format raises error."""
        mock_payload = {"sub": "not-a-valid-uuid"}

        with patch.object(TokenService, "decode_token", return_value=mock_payload):
            service = TokenService()
            with pytest.raises(TokenValidationError) as exc:
                service.get_user_id("test_token")

            assert "Invalid user ID format" in str(exc.value)

    def test_get_user_email_success(self):
        """Test successful email extraction."""
        mock_payload = {"sub": "550e8400-e29b-41d4-a716-446655440000", "email": "test@example.com"}

        with patch.object(TokenService, "decode_token", return_value=mock_payload):
            service = TokenService()
            result = service.get_user_email("test_token")

            assert result == "test@example.com"

    def test_get_user_email_missing(self):
        """Test missing email returns None."""
        mock_payload = {"sub": "550e8400-e29b-41d4-a716-446655440000"}  # No 'email' claim

        with patch.object(TokenService, "decode_token", return_value=mock_payload):
            service = TokenService()
            result = service.get_user_email("test_token")

            assert result is None


class TestTokenSingleton:
    """Tests for the token service singleton instance."""

    def test_singleton_exists(self):
        """Test that the singleton instance exists."""
        assert token_service is not None

    def test_singleton_is_token_service(self):
        """Test that the singleton is a TokenService instance."""
        assert isinstance(token_service, TokenService)
