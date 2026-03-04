"""Veritas API error types."""


class VeritasAPIError(Exception):
    """Raised when the Veritas API returns an error response (4xx or 5xx).

    Attributes:
        status_code: HTTP status code.
        code: Machine-readable error code from the API (e.g. INVALID_API_KEY).
        message: Human-readable error message.
        details: Optional additional context from the API.
        request_id: Request ID for debugging (from X-Request-Id or response body).
    """

    def __init__(
        self,
        status_code: int,
        error: dict,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = error.get("code", "UNKNOWN")
        self.message = error.get("message", "Unknown error")
        self.details = error.get("details")
        self.request_id = request_id
        super().__init__(f"[{self.code}] {self.message}")
