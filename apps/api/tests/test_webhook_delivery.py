"""Unit tests for webhook delivery: HMAC signing and retry logic."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.services.webhooks.delivery import (
    RETRY_DELAYS_SECONDS,
    build_signature_header,
    deliver_webhook,
    sign_payload,
)


class TestSignPayload:
    """Tests for sign_payload and build_signature_header."""

    def test_same_inputs_produce_same_signature(self):
        secret = "test-secret"
        payload_bytes = b'{"event":"doc.processed","payload":{}}'
        timestamp = 1234567890
        sig1 = sign_payload(secret, payload_bytes, timestamp)
        sig2 = sign_payload(secret, payload_bytes, timestamp)
        assert sig1 == sig2
        assert len(sig1) == 64
        assert all(c in "0123456789abcdef" for c in sig1)

    def test_different_secret_produces_different_signature(self):
        payload_bytes = b'{"event":"doc.processed"}'
        timestamp = 1234567890
        sig_a = sign_payload("secret-a", payload_bytes, timestamp)
        sig_b = sign_payload("secret-b", payload_bytes, timestamp)
        assert sig_a != sig_b

    def test_different_payload_produces_different_signature(self):
        secret = "secret"
        timestamp = 1234567890
        sig1 = sign_payload(secret, b'{"a":1}', timestamp)
        sig2 = sign_payload(secret, b'{"a":2}', timestamp)
        assert sig1 != sig2

    def test_different_timestamp_produces_different_signature(self):
        secret = "secret"
        payload_bytes = b"{}"
        sig1 = sign_payload(secret, payload_bytes, 1000)
        sig2 = sign_payload(secret, payload_bytes, 2000)
        assert sig1 != sig2

    def test_build_signature_header_format(self):
        secret = "my-secret"
        payload_bytes = b'{"event":"test"}'
        timestamp = 999888777
        header = build_signature_header(secret, payload_bytes, timestamp)
        assert header.startswith("t=999888777,v1=")
        hex_part = header.split(",v1=")[1]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)
        expected_sig = sign_payload(secret, payload_bytes, timestamp)
        assert hex_part == expected_sig

    def test_build_signature_header_without_timestamp_uses_current_time(self):
        secret = "secret"
        payload_bytes = b"{}"
        with patch("src.services.webhooks.delivery.time") as mock_time:
            mock_time.time.return_value = 111222333
            header = build_signature_header(secret, payload_bytes)
        assert "t=111222333," in header
        assert ",v1=" in header


class TestDeliverWebhookRetryLogic:
    """Tests for deliver_webhook retry behavior."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt_makes_single_post(self):
        with patch(
            "src.services.webhooks.delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_post = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            with patch(
                "src.services.webhooks.delivery.asyncio_sleep", new_callable=AsyncMock
            ) as mock_sleep:
                await deliver_webhook(
                    "https://example.com/hook",
                    "secret",
                    "document.processed",
                    {"document_id": "123"},
                )

        assert mock_post.await_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_four_times_on_failure(self):
        with patch(
            "src.services.webhooks.delivery.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_post = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_post.return_value = mock_resp
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            with patch(
                "src.services.webhooks.delivery.asyncio_sleep", new_callable=AsyncMock
            ) as mock_sleep:
                await deliver_webhook(
                    "https://example.com/hook",
                    "secret",
                    "test.event",
                    {},
                )

        assert mock_post.await_count == 4
        assert mock_sleep.await_count == 3
        delays = [c[0][0] for c in mock_sleep.await_args_list]
        assert delays == [5, 30, 300]
