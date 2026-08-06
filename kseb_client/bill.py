"""
Bill download functionality for KSEB Client SDK.

This module handles downloading bill PDFs from KSEB endpoints.
"""

import logging
from typing import TYPE_CHECKING

from .constants import BASE_URL, BILL_VIEW_URL, CONTENT_TYPE_PDF, FORM_FIELD_CONSUMER_NO, FORM_FIELD_MOBILE, FORM_FIELD_OKE_KEY, FORM_FIELD_SUBMIT, FORM_SUBMIT_VALUE
from .exceptions import KSEBAPIError, KSEBAuthenticationError, KSEBBillDownloadError, KSEBParsingError, KSEBValidationError
from .parser import extract_okey
from .utils import validate_consumer_no, validate_mobile

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def download_bill(session: "KSEBSession", consumer_no: str, mobile: str) -> bytes:
    """
    Download bill PDF for a consumer.

    The process:
    1. GET the bill view page to retrieve the OKE key
    2. Extract the hidden OKE key from the form
    3. POST the form with consumer details
    4. Return the PDF bytes

    Args:
        session: KSEBSession instance for making HTTP requests
        consumer_no: KSEB consumer number (13 digits)
        mobile: Mobile number associated with the consumer (10 digits)

    Returns:
        Bill PDF content as bytes

    Raises:
        KSEBValidationError: If inputs are invalid
        KSEBBillDownloadError: If bill download fails
        KSEBParsingError: If OKE key extraction fails
    """
    # Validate inputs
    if not validate_consumer_no(consumer_no):
        raise KSEBValidationError(f"Invalid consumer number format: {consumer_no}", field="consumer_no")

    if not validate_mobile(mobile):
        raise KSEBValidationError(f"Invalid mobile number format: {mobile}", field="mobile")

    logger.debug(f"Downloading bill for consumer: {consumer_no}")

    try:
        # Step 1: GET the bill view page
        logger.debug("Fetching bill view page to extract OKE key")
        response = session.get(BASE_URL)

        if response.status_code != 200:
            raise KSEBBillDownloadError(
                f"Failed to fetch bill view page: HTTP {response.status_code}"
            )

        # Step 2: Extract OKE key from the page
        try:
            okey = extract_okey(response.text)
        except KSEBParsingError as e:
            raise KSEBBillDownloadError(f"Failed to extract OKE key: {str(e)}") from e

        logger.debug("OKE key extracted successfully")

        # Step 3: POST the form to get the bill PDF
        logger.debug("Submitting bill download form")

        payload = {
            FORM_FIELD_CONSUMER_NO: consumer_no,
            FORM_FIELD_MOBILE: mobile,
            FORM_FIELD_OKE_KEY: okey,
            FORM_FIELD_SUBMIT: FORM_SUBMIT_VALUE,
        }

        response = session.post(BILL_VIEW_URL, data=payload)

        # Check if we got a PDF response
        content_type = response.headers.get("Content-Type", "")

        if CONTENT_TYPE_PDF not in content_type:
            if response.status_code == 200:
                # Might be an error page
                raise KSEBAuthenticationError(
                    "Failed to download bill: invalid consumer number or mobile number"
                )
            else:
                raise KSEBBillDownloadError(
                    f"Failed to download bill: HTTP {response.status_code}, "
                    f"Content-Type: {content_type}"
                )

        # Step 4: Return PDF bytes
        pdf_bytes = response.content

        if not pdf_bytes or len(pdf_bytes) < 100:  # PDF files should be larger
            raise KSEBBillDownloadError("Downloaded PDF is too small or invalid")

        logger.info(f"Bill downloaded successfully ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except (KSEBValidationError, KSEBBillDownloadError, KSEBAuthenticationError, KSEBParsingError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading bill: {e}")
        raise KSEBBillDownloadError(f"Failed to download bill: {str(e)}") from e
