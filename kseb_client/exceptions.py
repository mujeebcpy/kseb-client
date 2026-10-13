"""
Custom exceptions for KSEB Client SDK.

This module defines all custom exceptions raised by the SDK to provide
meaningful error handling and distinguish between different failure modes.
"""


class KSEBClientError(Exception):
    """Base exception for all KSEB Client errors."""

    pass


class KSEBAPIError(KSEBClientError):
    """Raised when the KSEB API returns an error or unexpected response."""

    def __init__(self, message: str, status_code: int | None = None, response: str | None = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class KSEBNetworkError(KSEBClientError):
    """Raised when there's a network-related issue (timeout, connection error, etc.)."""

    pass


class KSEBAuthenticationError(KSEBClientError):
    """Raised when authentication fails (invalid consumer number or mobile)."""

    pass


class KSEBValidationError(KSEBClientError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class KSEBParsingError(KSEBClientError):
    """Raised when parsing fails (PDF, HTML, JSON, etc.)."""

    def __init__(self, message: str, data_type: str | None = None):
        self.message = message
        self.data_type = data_type
        super().__init__(message)


class KSEBBillDownloadError(KSEBClientError):
    """Raised when bill download fails."""

    pass


class KSEBCaptchaError(KSEBClientError):
    """Raised when KSEB rejects a captcha answer (wrong or expired)."""

    pass


class KSEBTransformerNotFoundError(KSEBClientError):
    """Raised when a transformer cannot be found in the available list."""

    def __init__(self, message: str, transformer_name: str | None = None, section_code: str | None = None):
        self.message = message
        self.transformer_name = transformer_name
        self.section_code = section_code
        super().__init__(message)


class KSEBSectionNotFoundError(KSEBClientError):
    """Raised when section details cannot be found."""

    def __init__(self, message: str, consumer_no: str | None = None):
        self.message = message
        self.consumer_no = consumer_no
        super().__init__(message)
