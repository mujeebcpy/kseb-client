"""
Main KSEB Client class.

This module provides the primary public interface for interacting with KSEB APIs.
"""

import logging
import time
from difflib import SequenceMatcher
from typing import Optional

from .bill import download_bill, get_bill_captcha
from .constants import DEFAULT_CACHE_TTL
from .exceptions import (
    KSEBClientError,
    KSEBTransformerNotFoundError,
    KSEBValidationError,
)
from .models import (
    BillCaptcha,
    BillInfo,
    GridCapacityOptionsResult,
    GridCapacityResult,
    SectionInfo,
    Transformer,
    TransformerCaptcha,
)
from .parser import parse_bill_pdf
from .section import get_section
from .session import KSEBSession
from .transformer import find_transformer, get_transformer_captcha, get_transformers
from .utils import (
    extract_section_code,
    normalize_mobile,
    normalize_transformer_name,
    validate_consumer_no,
    validate_mobile,
)

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

    def get_bill_captcha(self) -> BillCaptcha:
        """Fetch a CAPTCHA challenge needed to download a bill."""
        return get_bill_captcha(self._session)

    def download_bill(
        self, consumer_no: str, mobile: str, *, captcha_code: str, session_id: str
    ) -> bytes:
        """
        Download bill PDF for a consumer.

        Args:
            consumer_no: KSEB consumer number (13 digits)
            mobile: Mobile number associated with the consumer (10 digits)
            captcha_code: User-entered answer for the bill CAPTCHA
            session_id: ``BillCaptcha.session_id`` returned by ``get_bill_captcha()``

        Returns:
            Bill PDF content as bytes

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBCaptchaError: If the captcha answer is wrong or expired
            KSEBClientError: If download fails
        """
        return download_bill(
            self._session, consumer_no, mobile, captcha_code=captcha_code, session_id=session_id
        )

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

    def get_transformer_captcha(self) -> TransformerCaptcha:
        """Fetch a CAPTCHA challenge needed to request transformer data."""
        return get_transformer_captcha(self._session)

    def get_transformers(
        self,
        section_code: str,
        use_cache: bool = True,
        section_info: Optional[SectionInfo] = None,
        *,
        captcha_code: Optional[str] = None,
        unique_id: Optional[str] = None,
    ) -> list[Transformer]:
        """
        Get list of available transformers for a section.

        Results are cached by default with TTL configurable via cache_ttl.

        Args:
            section_code: Section code (4-digit code)
            use_cache: Whether to use cached results. Defaults to True.
            section_info: Optional SectionInfo to enrich transformer data with division/subdivision
            captcha_code: CAPTCHA answer entered by the user (required on cache miss)
            unique_id: Unique ID from get_transformer_captcha() (required on cache miss)

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
        if not captcha_code or not unique_id:
            raise KSEBValidationError(
                "captcha_code and unique_id are required to fetch transformers",
                field="captcha_code",
            )
        transformers = get_transformers(
            self._session,
            section_code,
            section_info,
            captcha_code=captcha_code,
            unique_id=unique_id,
        )

        # Cache the result
        self._transformer_cache[section_code] = (transformers, time.time())

        return transformers

    def find_transformer(
        self, section_code: str, transformer_name: str, *,
        captcha_code: str, unique_id: str,
    ) -> Transformer:
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
        return find_transformer(
            self._session, section_code, transformer_name,
            captcha_code=captcha_code, unique_id=unique_id,
        )

    def get_grid_capacity(
        self,
        consumer_no: str,
        mobile: str,
        *,
        bill_captcha_code: str,
        bill_session_id: str,
        captcha_code: Optional[str] = None,
        unique_id: Optional[str] = None,
    ) -> GridCapacityResult:
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
            mobile: Mobile number associated with the consumer (10 digits or +91 followed by 10 digits)
            bill_captcha_code: Answer for the CAPTCHA from ``get_bill_captcha()``
            bill_session_id: ``BillCaptcha.session_id`` from ``get_bill_captcha()``
            captcha_code: Answer for the CAPTCHA from ``get_transformer_captcha()``
            unique_id: ``TransformerCaptcha.unique_id`` from ``get_transformer_captcha()``

        Returns:
            GridCapacityResult with section, bill, and transformer info

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBClientError: If any step fails
        """
        # Normalize mobile number (remove +91 if present)
        try:
            mobile = normalize_mobile(mobile)
        except ValueError as e:
            raise KSEBValidationError(f"Invalid mobile number: {mobile}") from e

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
            pdf_bytes = self.download_bill(
                consumer_no, mobile, captcha_code=bill_captcha_code, session_id=bill_session_id
            )

            # Step 3: Parse bill
            logger.debug("Step 3: Parsing bill")
            bill_info = self.parse_bill(pdf_bytes, consumer_no)

            # Step 4: Get transformers
            logger.debug("Step 4: Fetching transformer list")
            transformers = self.get_transformers(
                section_code,
                use_cache=True,
                section_info=section_info,
                captcha_code=captcha_code,
                unique_id=unique_id,
            )

            # Step 5: Find matching transformer
            logger.debug(f"Step 5: Finding transformer: {bill_info.dtr}")
            try:
                requested_name = normalize_transformer_name(bill_info.dtr)
                transformer = next(
                    (item for item in transformers if normalize_transformer_name(item.transformer_name) == requested_name),
                    None,
                )
                if transformer is None and transformers:
                    best_match = max(
                        transformers,
                        key=lambda item: SequenceMatcher(
                            None, requested_name, normalize_transformer_name(item.transformer_name)
                        ).ratio(),
                    )
                    if SequenceMatcher(
                        None, requested_name, normalize_transformer_name(best_match.transformer_name)
                    ).ratio() >= 0.6:
                        transformer = best_match
                if transformer is None:
                    raise KSEBTransformerNotFoundError(
                        f"Transformer not found: {bill_info.dtr}",
                        transformer_name=bill_info.dtr,
                        section_code=section_code,
                    )
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

    def get_grid_capacity_options(
        self, consumer_no: str, *, captcha_code: str, unique_id: str
    ) -> GridCapacityOptionsResult:
        """Get section details and all available transformer capacity options.

        This bill-free fallback is useful when the bill service is unavailable and
        an application needs to let a user select the correct transformer.
        """
        if not validate_consumer_no(consumer_no):
            raise KSEBValidationError(f"Invalid consumer number: {consumer_no}")

        try:
            section_code = extract_section_code(consumer_no)
            section_info = self.get_section(consumer_no)
            transformers = self.get_transformers(
                section_code,
                use_cache=True,
                section_info=section_info,
                captcha_code=captcha_code,
                unique_id=unique_id,
            )
            return GridCapacityOptionsResult(section=section_info, transformers=transformers)
        except KSEBClientError:
            raise
        except Exception as e:
            logger.error("Grid capacity options lookup failed: %s", e)
            raise KSEBClientError(f"Grid capacity lookup failed: {str(e)}") from e

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
