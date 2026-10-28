"""
KSEB Client SDK

A production-quality Python SDK for interacting with KSEB (Kerala State Electricity Board)
web services. Designed to be reusable across ERPNext, FastAPI, Flask, Django, desktop apps,
CLI tools, and other Python projects.

Example:
    >>> from kseb_client import KSEBClient
    >>> client = KSEBClient()
    >>> result = client.get_grid_capacity("1145657015077", "9895672251")
    >>> print(result.transformer.balance_available)

Installation:
    pip install kseb-client

Documentation:
    https://github.com/mujeebcpy/kseb-client
"""

from .client import KSEBClient
from .exceptions import (
    KSEBAPIError,
    KSEBAuthenticationError,
    KSEBBillDownloadError,
    KSEBCaptchaError,
    KSEBClientError,
    KSEBNetworkError,
    KSEBParsingError,
    KSEBSectionNotFoundError,
    KSEBTransformerNotFoundError,
    KSEBTurnstileError,
    KSEBValidationError,
)
from .models import (
    BillCaptcha,
    BillInfo,
    GridCapacityOptionsResult,
    GridCapacityResult,
    SectionInfo,
    Transformer,
)

__version__ = "1.0.0"
__author__ = "Your Name"
__all__ = [
    # Main client
    "KSEBClient",
    # Models
    "SectionInfo",
    "BillInfo",
    "BillCaptcha",
    "Transformer",
    "GridCapacityResult",
    "GridCapacityOptionsResult",
    # Exceptions
    "KSEBClientError",
    "KSEBAPIError",
    "KSEBNetworkError",
    "KSEBAuthenticationError",
    "KSEBValidationError",
    "KSEBParsingError",
    "KSEBBillDownloadError",
    "KSEBCaptchaError",
    "KSEBTurnstileError",
    "KSEBTransformerNotFoundError",
    "KSEBSectionNotFoundError",
]
