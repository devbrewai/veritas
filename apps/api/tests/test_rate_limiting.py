"""Tests for rate limiting middleware."""

import pytest

from src.middleware.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    LIMIT = 3

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create a rate limiter for testing."""
        return RateLimiter(max_requests=self.LIMIT, window_seconds=60)

    @pytest.fixture
    def user_a_id(self) -> str:
        """Test user A ID."""
        return "test-user-a"

    @pytest.fixture
    def user_b_id(self) -> str:
        """Test user B ID."""
        return "test-user-b"

    def test_rate_limit_allows_normal_usage(
        self, limiter: RateLimiter, user_a_id: str
    ):
        """Under limit succeeds."""
        limit = self.LIMIT
        assert limiter.check(user_a_id, limit) is True
        assert limiter.check(user_a_id, limit) is True
        assert limiter.check(user_a_id, limit) is True

    def test_rate_limit_blocks_excess(
        self, limiter: RateLimiter, user_a_id: str
    ):
        """Over limit returns False."""
        limit = self.LIMIT
        for _ in range(3):
            assert limiter.check(user_a_id, limit) is True
        assert limiter.check(user_a_id, limit) is False
        assert limiter.check(user_a_id, limit) is False

    def test_rate_limit_per_user(
        self, limiter: RateLimiter, user_a_id: str, user_b_id: str
    ):
        """Different users have separate limits."""
        limit = self.LIMIT
        for _ in range(3):
            assert limiter.check(user_a_id, limit) is True
        assert limiter.check(user_a_id, limit) is False
        assert limiter.check(user_b_id, limit) is True
        assert limiter.check(user_b_id, limit) is True
        assert limiter.check(user_b_id, limit) is True
        assert limiter.check(user_b_id, limit) is False

    def test_get_remaining_decrements(
        self, limiter: RateLimiter, user_a_id: str
    ):
        """Remaining count decreases with each request."""
        limit = self.LIMIT
        assert limiter.get_remaining(user_a_id, limit) == 3
        limiter.check(user_a_id, limit)
        assert limiter.get_remaining(user_a_id, limit) == 2
        limiter.check(user_a_id, limit)
        assert limiter.get_remaining(user_a_id, limit) == 1
        limiter.check(user_a_id, limit)
        assert limiter.get_remaining(user_a_id, limit) == 0
        limiter.check(user_a_id, limit)
        assert limiter.get_remaining(user_a_id, limit) == 0

    def test_reset_clears_count(
        self, limiter: RateLimiter, user_a_id: str
    ):
        """Reset allows user to start fresh."""
        limit = self.LIMIT
        for _ in range(3):
            limiter.check(user_a_id, limit)
        assert limiter.check(user_a_id, limit) is False
        limiter.reset(user_a_id, limit)
        assert limiter.check(user_a_id, limit) is True
        assert limiter.get_remaining(user_a_id, limit) == 2

    def test_different_window_sizes(self):
        """Different window sizes work correctly."""
        short_limiter = RateLimiter(max_requests=2, window_seconds=1)
        user_id = "test-user-window"
        limit = 2
        assert short_limiter.check(user_id, limit) is True
        assert short_limiter.check(user_id, limit) is True
        assert short_limiter.check(user_id, limit) is False

    def test_high_request_limit(self):
        """High request limits work correctly."""
        high_limiter = RateLimiter(max_requests=100, window_seconds=60)
        user_id = "test-user-high-limit"
        limit = 100
        for _ in range(100):
            assert high_limiter.check(user_id, limit) is True

        # 101st should fail
        assert high_limiter.check(user_id, limit) is False


class TestRateLimiterConcurrency:
    """Tests for rate limiter with multiple users."""

    def test_many_users_tracked(self):
        """Can track many users simultaneously."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        users = [f"test-user-{i}" for i in range(100)]
        limit = 5

        for user in users:
            for _ in range(5):
                assert limiter.check(user, limit) is True
            assert limiter.check(user, limit) is False

    def test_user_isolation(self):
        """One user's rate limit doesn't affect another."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limit = 2
        user_a = "test-user-isolation-a"
        user_b = "test-user-isolation-b"

        assert limiter.check(user_a, limit) is True
        assert limiter.check(user_b, limit) is True
        assert limiter.check(user_a, limit) is True
        assert limiter.check(user_b, limit) is True
        assert limiter.check(user_a, limit) is False
        assert limiter.check(user_b, limit) is False
