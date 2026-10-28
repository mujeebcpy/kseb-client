"""
Main KSEB Client class.

This module provides the primary public interface for interacting with KSEB APIs.
"""

import logging
from typing import Optional

from .bill import download_bill, get_bill_captcha
from .exceptions import (
    KSEBClientError,
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
from .parser import parse_bill_pdf
from .section import get_section
from .session import KSEBSession
from .transformer import get_transformer
from .utils import normalize_mobile, validate_consumer_no, validate_mobile

logger = logging.getLogger(__name__)


class KSEBClient:
    """
    KSEB Client for accessing KSEB web services.

    This is the main entry point for the SDK. All HTTP communication goes through
    a shared requests.Session with automatic retry logic.

    Example:
        >>> client = KSEBClient()
        >>> result = client.get_grid_capacity(
        ...     "1145657015077", "9895672251",
        ...     bill_captcha_code=code, bill_session_id=captcha.session_id,
        ...     turnstile_token=token,
        ... )
        >>> print(result.transformer.balance_available)
    """

    def __init__(
        self,
        timeout: int = 15,
        retries: int = 3,
        backoff_factor: float = 0.3,
    ):
        """
        Initialize KSEB Client.

        Args:
            timeout: HTTP request timeout in seconds. Defaults to 15.
            retries: Number of retries for failed requests. Defaults to 3.
            backoff_factor: Exponential backoff multiplier. Defaults to 0.3.
        """
        self._session = KSEBSession(timeout=timeout, retries=retries, backoff_factor=backoff_factor)

        logger.debug(
            f"KSEBClient initialized: timeout={timeout}s, retries={retries}, "
            f"backoff={backoff_factor}"
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

    def get_transformer(
        self,
        consumer_no: str,
        *,
        turnstile_token: str,
        section_info: Optional[SectionInfo] = None,
    ) -> Transformer:
        """
        Get the transformer serving a consumer, with its solar capacity.

        Args:
            consumer_no: KSEB consumer number (13 digits)
            turnstile_token: ``cf-turnstile-response`` from the Cloudflare Turnstile
                check on the KSEB website (single use)
            section_info: Optional SectionInfo to fill in division/subdivision

        Returns:
            Transformer object

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBTurnstileError: If KSEB rejects the Turnstile token
            KSEBClientError: If request fails
        """
        return get_transformer(
            self._session, consumer_no, turnstile_token=turnstile_token, section_info=section_info
        )

    def get_grid_capacity(
        self,
        consumer_no: str,
        mobile: str,
        *,
        bill_captcha_code: str,
        bill_session_id: str,
        turnstile_token: str,
    ) -> GridCapacityResult:
        """
        High-level helper to get complete grid capacity information.

        This method:
        1. Fetches section details
        2. Downloads and parses bill
        3. Fetches the consumer's transformer
        4. Returns complete result

        Args:
            consumer_no: KSEB consumer number (13 digits)
            mobile: Mobile number associated with the consumer (10 digits or +91 followed by 10 digits)
            bill_captcha_code: Answer for the CAPTCHA from ``get_bill_captcha()``
            bill_session_id: ``BillCaptcha.session_id`` from ``get_bill_captcha()``
            turnstile_token: ``cf-turnstile-response`` from the Turnstile check on the KSEB website

        Returns:
            GridCapacityResult with section, bill, and transformer info

        Raises:
            KSEBValidationError: If inputs are invalid
            KSEBTurnstileError: If KSEB rejects the Turnstile token
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

            # Step 4: Get the consumer's transformer
            logger.debug("Step 4: Fetching transformer")
            transformer = self.get_transformer(
                consumer_no, turnstile_token=turnstile_token, section_info=section_info
            )

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
        self, consumer_no: str, *, turnstile_token: str
    ) -> GridCapacityOptionsResult:
        """Get section details and the consumer's transformer without downloading a bill.

        KSEB now returns only the consumer's own transformer, so ``transformers``
        holds a single item.
        """
        if not validate_consumer_no(consumer_no):
            raise KSEBValidationError(f"Invalid consumer number: {consumer_no}")

        try:
            section_info = self.get_section(consumer_no)
            transformer = self.get_transformer(
                consumer_no, turnstile_token=turnstile_token, section_info=section_info
            )
            return GridCapacityOptionsResult(section=section_info, transformers=[transformer])
        except KSEBClientError:
            raise
        except Exception as e:
            logger.error("Grid capacity options lookup failed: %s", e)
            raise KSEBClientError(f"Grid capacity lookup failed: {str(e)}") from e

    def close(self) -> None:
        """Close the client and release resources."""
        self._session.close()
        logger.debug("KSEBClient closed")

    def __enter__(self) -> "KSEBClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
