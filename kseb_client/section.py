"""
Section information retrieval from KSEB endpoints.

This module handles fetching and parsing section details for a given consumer number.
"""

import logging
from typing import TYPE_CHECKING

from .constants import SECTION_URL
from .exceptions import KSEBAPIError, KSEBParsingError, KSEBSectionNotFoundError, KSEBValidationError
from .models import SectionInfo
from .parser import parse_section_html
from .utils import validate_consumer_no

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def get_section(session: "KSEBSession", consumer_no: str) -> SectionInfo:
    """
    Fetch section details for a consumer number.

    Args:
        session: KSEBSession instance for making HTTP requests
        consumer_no: KSEB consumer number (13 digits)

    Returns:
        SectionInfo object with section details

    Raises:
        KSEBValidationError: If consumer_no is invalid
        KSEBAPIError: If API request fails
        KSEBSectionNotFoundError: If section not found
        KSEBParsingError: If response parsing fails
    """
    # Validate input
    if not validate_consumer_no(consumer_no):
        raise KSEBValidationError(f"Invalid consumer number format: {consumer_no}", field="consumer_no")

    logger.debug(f"Fetching section details for consumer: {consumer_no}")

    try:
        # Make API request
        response = session.get(SECTION_URL, params={"consumerno": consumer_no})

        # Check response status
        if response.status_code != 200:
            raise KSEBAPIError(
                f"Section details request failed",
                status_code=response.status_code,
                response=response.text[:500],
            )

        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            raise KSEBParsingError(f"Failed to parse JSON response: {str(e)}", data_type="JSON") from e

        # Extract HTML from response
        if "msg" not in data:
            raise KSEBSectionNotFoundError(f"Section not found for consumer: {consumer_no}", consumer_no=consumer_no)

        html = data["msg"]

        # Parse HTML to extract section details
        details = parse_section_html(html)

        # Validate required fields
        required_fields = ["section", "division", "subdivision"]
        missing = [f for f in required_fields if not details.get(f)]

        if missing:
            logger.warning(f"Missing fields in section response: {missing}")

        # Create SectionInfo object
        section_info = SectionInfo(
            office_code=details.get("office_code", ""),
            section=details.get("section", ""),
            subdivision=details.get("subdivision", ""),
            subdivision_email=details.get("subdivision_email", ""),
            division=details.get("division", ""),
            division_phone=details.get("division_phone", ""),
            division_email=details.get("division_email", ""),
            phone=details.get("phone", ""),
            email=details.get("email", ""),
        )

        logger.info(f"Section details retrieved: {section_info.section}")
        return section_info

    except (KSEBValidationError, KSEBAPIError, KSEBSectionNotFoundError, KSEBParsingError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching section: {e}")
        raise KSEBAPIError(f"Failed to get section details: {str(e)}") from e
