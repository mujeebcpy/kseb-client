"""
Parsing utilities for extracting data from HTML and PDF documents.

This module handles extraction of structured data from KSEB web responses and PDF bills.
"""

import logging
import re
from io import BytesIO
from typing import Any

import pdfplumber
from bs4 import BeautifulSoup

from .exceptions import KSEBParsingError
from .models import BillInfo

logger = logging.getLogger(__name__)


def parse_section_html(html: str) -> dict[str, str | None]:
    """
    Parse HTML response from section detail endpoint.

    Args:
        html: HTML content to parse

    Returns:
        Dictionary containing section details

    Raises:
        KSEBParsingError: If parsing fails
    """
    try:
        details: dict[str, str | None] = {}

        # Extract Section (after "Electrical Section")
        section_match = re.search(
            r"Section Ofiice:\s*Electrical Section\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["office_code"] = None
        details["section"] = section_match.group(1).strip() if section_match else None

        # Extract Phone
        phone_match = re.search(
            r"Phone:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["phone"] = phone_match.group(1).strip() if phone_match else None

        # Extract Email
        email_match = re.search(
            r"Email:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["email"] = email_match.group(1).strip() if email_match else None

        # Extract Sub Division
        subdivision_match = re.search(
            r"Sub Division:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["subdivision"] = subdivision_match.group(1).strip() if subdivision_match else None

        # Extract Sub Division Email
        subemail_match = re.search(
            r"Sub Division Email:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["subdivision_email"] = subemail_match.group(1).strip() if subemail_match else None

        # Extract Division (use negative lookbehind to avoid matching "Sub Division")
        division_match = re.search(
            r"(?<!Sub )Division:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["division"] = division_match.group(1).strip() if division_match else None

        # Extract Division Phone
        divphone_match = re.search(
            r"(?<!Sub )Division Phone:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["division_phone"] = divphone_match.group(1).strip() if divphone_match else None

        # Extract Division Email
        divemail_match = re.search(
            r"(?<!Sub )Division Email:\s*(.*?)<br>",
            html,
            re.IGNORECASE,
        )
        details["division_email"] = divemail_match.group(1).strip() if divemail_match else None

        logger.debug(f"Parsed section details: {details}")
        return details

    except Exception as e:
        logger.error(f"Failed to parse section HTML: {e}")
        raise KSEBParsingError(f"Failed to parse section details: {str(e)}", data_type="HTML") from e


def extract_okey(html: str) -> str:
    """
    Extract the OKE key from bill view page HTML.

    Args:
        html: HTML content of the bill view page

    Returns:
        OKE key value

    Raises:
        KSEBParsingError: If OKE key cannot be found
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        okey_input = soup.find("input", {"name": "okey"})

        if okey_input is None or "value" not in okey_input.attrs:
            raise KSEBParsingError("Cannot find OKE key in page", data_type="HTML")

        okey = okey_input["value"]
        logger.debug(f"Extracted OKE key: {okey[:10]}..." if len(str(okey)) > 10 else f"Extracted OKE key: {okey}")
        return str(okey)

    except KSEBParsingError:
        raise
    except Exception as e:
        logger.error(f"Failed to extract OKE key: {e}")
        raise KSEBParsingError(f"Failed to extract OKE key: {str(e)}", data_type="HTML") from e


def parse_bill_pdf(pdf_bytes: bytes, consumer_no: str) -> BillInfo:
    """
    Extract information from a KSEB bill PDF.

    Args:
        pdf_bytes: PDF file content as bytes
        consumer_no: Consumer number for validation

    Returns:
        BillInfo object with extracted data

    Raises:
        KSEBParsingError: If PDF parsing or required fields are missing
    """
    try:
        # Read PDF from bytes
        pdf_file = BytesIO(pdf_bytes)

        with pdfplumber.open(pdf_file) as pdf:
            # Extract text from all pages
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            logger.debug(f"Extracted {len(text)} characters from PDF")

            # Extract consumer name
            consumer_name = _extract_consumer_name(text)

            # Extract section
            section = _extract_section(text)

            # Extract DTR
            dtr = _extract_dtr(text)

            # Extract connected load
            connected_load = _extract_connected_load(text)

            # Extract tariff and phase
            tariff = _extract_tariff(text)
            phase = _extract_phase(text)

            # Extract customer address
            customer_address = _extract_customer_address(text)

            if not dtr:
                raise KSEBParsingError("DTR information not found in PDF", data_type="PDF")

            bill_info = BillInfo(
                consumer_no=consumer_no,
                consumer_name=consumer_name or "Unknown",
                section=section or "Unknown",
                dtr=dtr,
                connected_load=connected_load,
                tariff=tariff,
                phase=phase,
                customer_address=customer_address,
            )

            logger.debug(f"Parsed bill: {bill_info}")
            return bill_info

    except KSEBParsingError:
        raise
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        raise KSEBParsingError(f"Failed to parse bill PDF: {str(e)}", data_type="PDF") from e


def _extract_consumer_name(text: str) -> str | None:
    """Extract consumer name from 'Name & Mailing Address' section of bill text."""
    # Look for "Name & Mailing Address" and get the next line, stopping at CGRF markers (South/Central/North)
    match = re.search(
        r"Name\s*&\s*Mailing\s+Address[^\n]*\n\s*([^\n:]+?)(?:\s+(?:South|Central|North):|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        if name and len(name) > 2:
            return name

    # Fallback to alternative patterns if primary pattern doesn't match
    matches = [
        re.search(r"Consumer Name\s*:?\s*([^\n\r]+)", text, re.IGNORECASE),
        re.search(r"Consumners\s*Name\s*:?\s*([^\n\r]+)", text, re.IGNORECASE),
    ]

    for match in matches:
        if match:
            name = match.group(1).strip()
            if name and len(name) > 2:
                return name

    return None


def _extract_section(text: str) -> str | None:
    """Extract section from bill text."""
    match = re.search(
        r"Electrical Section\s+(.+?)\s+Phone#",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        section = match.group(1).strip()
        # Clean up extra whitespace
        section = re.sub(r"\s+", " ", section)
        return section

    return None


def _extract_dtr(text: str) -> str | None:
    """Extract DTR from bill text, capturing all data after DTR."""
    match = re.search(
        r"DTR\s+(.+)",
        text,
        re.IGNORECASE,
    )
    if match:
        dtr = match.group(1).strip()
        return dtr if dtr else None

    return None


def _extract_connected_load(text: str) -> str | None:
    """Extract connected load from bill text."""
    matches = [
        re.search(r"Connected Load\s*:?\s*([^\n\r]+)", text, re.IGNORECASE),
        re.search(r"CT Ratio\s*:?\s*([^\n\r]+)", text, re.IGNORECASE),
    ]

    for match in matches:
        if match:
            load = match.group(1).strip()
            if load:
                return load

    return None


def _extract_tariff(text: str) -> str | None:
    """Extract tariff from bill text."""
    match = re.search(
        r"Tariff\s*:?\s*([^\n\r/]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        tariff = match.group(1).strip()
        return tariff

    return None


def _extract_phase(text: str) -> str | None:
    """Extract phase details from bill text."""
    # Look for phase information in tariff line or separately
    match = re.search(
        r"(?:Tariff\s*[:/]?\s*)?Phase\s*:?\s*([^\n\r]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        phase = match.group(1).strip()
        return phase

    # Also try to extract phase from tariff/phase combined field
    match = re.search(
        r"Tariff\s*[:/]\s*Phase\s*:?\s*([^\n\r]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        phase = match.group(1).strip()
        return phase

    return None


def _extract_customer_address(text: str) -> str | None:
    """Extract customer address following Name & Mailing Address field."""
    # Look for "Name & Mailing Address" and skip first line (name), then get the address line
    # Stop at CGRF markers (South/Central/North)
    match = re.search(
        r"Name\s*&\s*Mailing\s+Address[^\n]*\n[^\n]+\n\s*([^\n:]+?)(?:\s+(?:South|Central|North):|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        address = match.group(1).strip()
        if address:
            return address

    return None
