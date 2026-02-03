"""Tests for rate limiting middleware."""

import uuid

import pytest

from src.middleware.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create a rate limiter for testing."""
        return RateLimiter(max_requests=3, window_seconds=60)

    @pytest.fixture
    def user_a_id(self) -> uuid.UUID:
        """Test user A ID."""
        return uuid.UUID("00000000-0000-0000-0000-000000000001")

    @pytest.fixture
    def user_b_id(self) -> uuid.UUID:
        """Test user B ID."""
        return uuid.UUID("00000000-0000-0000-0000-000000000002")

    def test_rate_limit_allows_normal_usage(
        self, limiter: RateLimiter, user_a_id: uuid.UUID
    ):
        """Under limit succeeds."""
        # First 3 requests should succeed
        assert limiter.check(user_a_id) is True
        assert limiter.check(user_a_id) is True
        assert limiter.check(user_a_id) is True

    def test_rate_limit_blocks_excess(
        self, limiter: RateLimiter, user_a_id: uuid.UUID
    ):
        """Over limit returns False."""
        # Use up the limit
        for _ in range(3):
            assert limiter.check(user_a_id) is True

        # 4th request should be blocked
        assert limiter.check(user_a_id) is False
        assert limiter.check(user_a_id) is False

    def test_rate_limit_per_user(
        self, limiter: RateLimiter, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ):
        """Different users have separate limits."""
        # Use up User A's limit
        for _ in range(3):
            assert limiter.check(user_a_id) is True

        # User A should be blocked
        assert limiter.check(user_a_id) is False

        # User B should still have their limit
        assert limiter.check(user_b_id) is True
        assert limiter.check(user_b_id) is True
        assert limiter.check(user_b_id) is True

        # Now User B should be blocked
        assert limiter.check(user_b_id) is False

    def test_get_remaining_decrements(
        self, limiter: RateLimiter, user_a_id: uuid.UUID
    ):
        """Remaining count decreases with each request."""
        assert limiter.get_remaining(user_a_id) == 3

        limiter.check(user_a_id)
        assert limiter.get_remaining(user_a_id) == 2

        limiter.check(user_a_id)
        assert limiter.get_remaining(user_a_id) == 1

        limiter.check(user_a_id)
        assert limiter.get_remaining(user_a_id) == 0

        # After limit exceeded, remaining stays at 0
        limiter.check(user_a_id)
        assert limiter.get_remaining(user_a_id) == 0

    def test_reset_clears_count(
        self, limiter: RateLimiter, user_a_id: uuid.UUID
    ):
        """Reset allows user to start fresh."""
        # Use up the limit
        for _ in range(3):
            limiter.check(user_a_id)

        # User is blocked
        assert limiter.check(user_a_id) is False

        # Reset the user's limit
        limiter.reset(user_a_id)

        # User can now make requests again
        assert limiter.check(user_a_id) is True
        assert limiter.get_remaining(user_a_id) == 2

    def test_different_window_sizes(self):
        """Different window sizes work correctly."""
        # Very short window for testing
        short_limiter = RateLimiter(max_requests=2, window_seconds=1)
        user_id = uuid.uuid4()

        assert short_limiter.check(user_id) is True
        assert short_limiter.check(user_id) is True
        assert short_limiter.check(user_id) is False

    def test_high_request_limit(self):
        """High request limits work correctly."""
        high_limiter = RateLimiter(max_requests=100, window_seconds=60)
        user_id = uuid.uuid4()

        # Should allow 100 requests
        for _ in range(100):
            assert high_limiter.check(user_id) is True

        # 101st should fail
        assert high_limiter.check(user_id) is False


class TestRateLimiterConcurrency:
    """Tests for rate limiter with multiple users."""

    def test_many_users_tracked(self):
        """Can track many users simultaneously."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        users = [uuid.uuid4() for _ in range(100)]

        # Each user can make 5 requests
        for user in users:
            for _ in range(5):
                assert limiter.check(user) is True

            # 6th request fails
            assert limiter.check(user) is False

    def test_user_isolation(self):
        """One user's rate limit doesn't affect another."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        # Alternate between users
        assert limiter.check(user_a) is True
        assert limiter.check(user_b) is True
        assert limiter.check(user_a) is True
        assert limiter.check(user_b) is True

        # Both hit limit at the same time
        assert limiter.check(user_a) is False
        assert limiter.check(user_b) is False
