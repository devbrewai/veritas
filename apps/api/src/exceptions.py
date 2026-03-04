"""Custom API exceptions for standardized error responses."""


class VeritasError(Exception):
    """Raised for API errors that should return ErrorResponse shape with request_id."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)
