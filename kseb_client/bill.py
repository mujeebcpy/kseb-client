"""
Bill download functionality for KSEB Client SDK.

This module handles downloading bill PDFs from the kseb.in "Know your bill" service.
"""

import base64
import binascii
import logging
import re
from typing import TYPE_CHECKING

from .constants import (
    BILL_CAPTCHA_URL,
    BILL_DETAIL_URL,
    BILL_SESSION_COOKIE,
    FORM_FIELD_CAPTCHA,
    FORM_FIELD_CONSUMER_NO,
    FORM_FIELD_MOBILE,
)
from .exceptions import (
    KSEBAuthenticationError,
    KSEBBillDownloadError,
    KSEBCaptchaError,
    KSEBParsingError,
    KSEBValidationError,
)
from .models import BillCaptcha
from .utils import validate_consumer_no, validate_mobile, normalize_mobile

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def get_bill_captcha(session: "KSEBSession") -> BillCaptcha:
    """
    Fetch a CAPTCHA image for bill download.

    kseb.in stores the expected answer in the server-side session, identified by
    the ``kseb_session`` cookie. The query string the website appends to the
    captcha URL is only a cache-buster and is not needed.

    Each captcha can be submitted once; fetch a new one after a failed attempt.
    """
    try:
        # Send no cookies so KSEB starts a fresh session for every captcha. Reusing
        # the shared cookie jar would let concurrent users overwrite each other's answer.
        response = session.get(BILL_CAPTCHA_URL, headers={"Cookie": ""})
        if not response.content:
            raise KSEBParsingError("Captcha image response was empty", data_type="image")

        session_id = response.cookies.get(BILL_SESSION_COOKIE)
        if not session_id:
            raise KSEBParsingError("KSEB did not return a session cookie with the captcha", data_type="cookie")

        return BillCaptcha(
            session_id=session_id,
            image=response.content,
            content_type=response.headers.get("Content-Type"),
        )
    except KSEBParsingError:
        raise
    except Exception as e:
        raise KSEBBillDownloadError(f"Failed to fetch bill captcha: {e}") from e


def download_bill(
    session: "KSEBSession",
    consumer_no: str,
    mobile: str,
    *,
    captcha_code: str,
    session_id: str,
) -> bytes:
    """
    Download bill PDF for a consumer.

    The process:
    1. GET the bill detail endpoint with consumer details and the captcha answer,
       in the KSEB session the captcha was issued for
    2. Decode the base64 PDF from the JSON response

    Args:
        session: KSEBSession instance for making HTTP requests
        consumer_no: KSEB consumer number (13 digits)
        mobile: Mobile number associated with the consumer (10 digits or +91 followed by 10 digits)
        captcha_code: User-entered CAPTCHA answer
        session_id: ``BillCaptcha.session_id`` returned with the CAPTCHA

    Returns:
        Bill PDF content as bytes

    Raises:
        KSEBValidationError: If inputs are invalid
        KSEBCaptchaError: If the captcha answer is wrong or expired
        KSEBAuthenticationError: If KSEB rejects the consumer number / mobile
        KSEBBillDownloadError: If bill download fails
    """
    # Normalize mobile number (remove +91 if present)
    try:
        mobile = normalize_mobile(mobile)
    except ValueError as e:
        raise KSEBValidationError(f"Invalid mobile number format: {mobile}") from e

    # Validate inputs
    if not validate_consumer_no(consumer_no):
        raise KSEBValidationError(f"Invalid consumer number format: {consumer_no}", field="consumer_no")

    if not validate_mobile(mobile):
        raise KSEBValidationError(f"Invalid mobile number format: {mobile}", field="mobile")

    if not isinstance(captcha_code, str) or not captcha_code.strip():
        raise KSEBValidationError("Captcha answer is required", field="captcha_code")

    if not isinstance(session_id, str) or not session_id.strip():
        raise KSEBValidationError("Captcha session ID is required", field="session_id")

    logger.debug(f"Downloading bill for consumer: {consumer_no}")

    try:
        # Step 1: Request the bill in the captcha's session. The cookie is sent as an
        # explicit header (which bypasses the shared cookie jar) so concurrent
        # requests on one client cannot mix up sessions.
        params = {
            FORM_FIELD_CONSUMER_NO: consumer_no,
            FORM_FIELD_MOBILE: mobile,
            FORM_FIELD_CAPTCHA: captcha_code.strip(),
        }
        response = session.get(
            BILL_DETAIL_URL,
            params=params,
            headers={
                "Cookie": f"{BILL_SESSION_COOKIE}={session_id.strip()}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )

        try:
            data = response.json()
        except ValueError as e:
            raise KSEBBillDownloadError(
                f"Unexpected bill response: Content-Type {response.headers.get('Content-Type', '')}"
            ) from e

        # Step 2: Decode the PDF
        pdf_data = data.get("pdf_file_data") if isinstance(data, dict) else None
        if not pdf_data:
            message = _strip_html(data.get("msg", "") if isinstance(data, dict) else str(data))
            if "captcha" in message.lower():
                raise KSEBCaptchaError(message or "Invalid captcha")
            raise KSEBAuthenticationError(
                message or "Failed to download bill: invalid consumer number or mobile number"
            )

        try:
            pdf_bytes = base64.b64decode(pdf_data, validate=True)
        except (binascii.Error, ValueError) as e:
            raise KSEBBillDownloadError("Bill PDF data is not valid base64") from e

        if not pdf_bytes.startswith(b"%PDF"):
            raise KSEBBillDownloadError("Downloaded bill is not a PDF")

        logger.info(f"Bill downloaded successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except (KSEBValidationError, KSEBBillDownloadError, KSEBAuthenticationError, KSEBCaptchaError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading bill: {e}")
        raise KSEBBillDownloadError(f"Failed to download bill: {str(e)}") from e


def _strip_html(text: str) -> str:
    """Convert the HTML snippet in KSEB's ``msg`` field to plain text."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
