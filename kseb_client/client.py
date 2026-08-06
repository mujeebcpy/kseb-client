"""
Main KSEB Client class.

This module provides the primary public interface for interacting with KSEB APIs.
"""

import logging
import time
from typing import Optional

from .bill import download_bill
from .constants import DEFAULT_CACHE_TTL
from .exceptions import (
    KSEBClientError,
    KSEBTransformerNotFoundError,
    KSEBValidationError,
)
from .models import BillInfo, GridCapacityResult, SectionInfo, Transformer
from .parser import parse_bill_pdf
from .section import get_section
from .session import KSEBSession
from .transformer import find_transformer, get_transformers
from .utils import extract_section_code, validate_consumer_no, validate_mobile

logger = logging.getLogger(__name__)


class KSEBClient:
    """
    KSEB Client for accessing KSEB web services.

    This is the main entry point for the SDK. All HTTP communication goes through
    a shared requests.Session with automatic retry logic.

    Example:
        >>> client = KSEBClient()
        >>> result = client.get_grid_capacity("1145657015077", "9895672251")
        >>> print(result.transformer.balance_available)
    """

    def __init__(
        self,
        timeout: int = 15,
        retries: int = 3,
        backoff_factor: float = 0.3,
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        """
        Initialize KSEB Client.

        Args:
            timeout: HTTP request timeout in seconds. Defaults to 15.
            retries: Number of retries for failed requests. Defaults to 3.
            backoff_factor: Exponential backoff multiplier. Defaults to 0.3.
            cache_ttl: Cache TTL for transformer lists in seconds. Defaults to 900 (15 min).
        """
        self._session = KSEBSession(timeout=timeout, retries=retries, backoff_factor=backoff_factor)
        self.cache_ttl = cache_ttl
        self._transformer_cache: dict[str, tuple[list[Transformer], float]] = {}

        logger.debug(
            f"KSEBClient initialized: timeout={timeout}s, retries={retries}, "
            f"backoff={backoff_factor}, cache_ttl={cache_ttl}s"
        )

    def get_section(self, consumer_no: str) -> SectionInfo:
        """
        Get section details for a consumer.

        Args:
            consumer_no: KSEB consumer number (13 digits)

        Returns:
            SectionInfo object with section details

        Raises:
            KSEBValidationError: If consumer_no is invalid
            KSEBClientError: If request fails
        """
        return get_section(self._session, consumer_no)

    def download_bill(self, consumer_no: str, mobile: str) -> bytes:
        """
        Download bill PDF for a consumer.

        Args:
            consumer_no: KSEB consumer number (13 digits)
            mobile: Mobile number associated with the consumer (10 digits)

        Returns:
            Bill PDF content as bytes

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBClientError: If download fails
        """
        return download_bill(self._session, consumer_no, mobile)

    def parse_bill(self, pdf_bytes: bytes, consumer_no: str) -> BillInfo:
        """
        Parse bill information from PDF bytes.

        Args:
            pdf_bytes: Bill PDF content as bytes
            consumer_no: Consumer number for validation

        Returns:
            BillInfo object with extracted information

        Raises:
            KSEBValidationError: If consumer_no is invalid
            KSEBClientError: If parsing fails
        """
        if not validate_consumer_no(consumer_no):
            raise KSEBValidationError(f"Invalid consumer number: {consumer_no}")

        return parse_bill_pdf(pdf_bytes, consumer_no)

    def get_transformers(self, section_code: str, use_cache: bool = True, section_info: Optional[SectionInfo] = None) -> list[Transformer]:
        """
        Get list of available transformers for a section.

        Results are cached by default with TTL configurable via cache_ttl.

        Args:
            section_code: Section code (4-digit code)
            use_cache: Whether to use cached results. Defaults to True.
            section_info: Optional SectionInfo to enrich transformer data with division/subdivision

        Returns:
            List of Transformer objects

        Raises:
            KSEBValidationError: If section_code is invalid
            KSEBClientError: If request fails
        """
        # Check cache first
        if use_cache and section_code in self._transformer_cache:
            transformers, timestamp = self._transformer_cache[section_code]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Returning cached transformers for section {section_code}")
                return transformers

        # Fetch from API
        transformers = get_transformers(self._session, section_code, section_info)

        # Cache the result
        self._transformer_cache[section_code] = (transformers, time.time())

        return transformers

    def find_transformer(self, section_code: str, transformer_name: str) -> Transformer:
        """
        Find a specific transformer by name.

        Args:
            section_code: Section code (4-digit code)
            transformer_name: Transformer name/ID

        Returns:
            Transformer object if found

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBTransformerNotFoundError: If transformer not found
            KSEBClientError: If request fails
        """
        return find_transformer(self._session, section_code, transformer_name)

    def get_grid_capacity(self, consumer_no: str, mobile: str) -> GridCapacityResult:
        """
        High-level helper to get complete grid capacity information.

        This method:
        1. Extracts section code from consumer number
        2. Fetches section details
        3. Downloads and parses bill
        4. Fetches available transformers
        5. Matches the consumer's transformer
        6. Returns complete result

        Args:
            consumer_no: KSEB consumer number (13 digits)
            mobile: Mobile number associated with the consumer (10 digits)

        Returns:
            GridCapacityResult with section, bill, and transformer info

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBClientError: If any step fails
        """
        # Validate inputs
        if not validate_consumer_no(consumer_no):
            raise KSEBValidationError(f"Invalid consumer number: {consumer_no}")

        if not validate_mobile(mobile):
            raise KSEBValidationError(f"Invalid mobile number: {mobile}")

        logger.info(f"Getting grid capacity for consumer: {consumer_no}")

        try:
            # Get section code
            section_code = extract_section_code(consumer_no)

            # Step 1: Get section details
            logger.debug("Step 1: Fetching section details")
            section_info = self.get_section(consumer_no)

            # Step 2: Download bill
            logger.debug("Step 2: Downloading bill")
            pdf_bytes = self.download_bill(consumer_no, mobile)

            # Step 3: Parse bill
            logger.debug("Step 3: Parsing bill")
            bill_info = self.parse_bill(pdf_bytes, consumer_no)

            # Step 4: Get transformers
            logger.debug("Step 4: Fetching transformer list")
            transformers = self.get_transformers(section_code, use_cache=True, section_info=section_info)

            # Step 5: Find matching transformer
            logger.debug(f"Step 5: Finding transformer: {bill_info.dtr}")
            try:
                transformer = self.find_transformer(section_code, bill_info.dtr)
            except KSEBTransformerNotFoundError:
                logger.warning(
                    f"Exact transformer match not found for {bill_info.dtr}. "
                    f"Available: {[t.transformer_name for t in transformers[:5]]}"
                )
                raise

            # Combine results
            result = GridCapacityResult(
                section=section_info,
                bill=bill_info,
                transformer=transformer,
            )

            logger.info(f"Grid capacity result: {result}")
            return result

        except KSEBClientError:
            raise
        except Exception as e:
            logger.error(f"Grid capacity query failed: {e}")
            raise KSEBClientError(f"Grid capacity query failed: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear the transformer cache."""
        self._transformer_cache.clear()
        logger.debug("Transformer cache cleared")

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        self._transformer_cache.clear()
        logger.debug("KSEBClient closed")

    def __enter__(self) -> "KSEBClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
