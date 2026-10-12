"""
Transformer information retrieval from KSEB endpoints.

This module handles fetching and matching transformer details.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Optional

from .constants import DTR_AVAILABLE_URL, TRANSFORMER_CAPTCHA_URL, TRANSFORMER_UNIQUE_ID_URL
from .exceptions import KSEBAPIError, KSEBParsingError, KSEBTransformerNotFoundError, KSEBValidationError
from .models import SectionInfo, Transformer, TransformerCaptcha
from .utils import extract_section_code, normalize_transformer_name, parse_capacity_value, validate_consumer_no

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def get_transformer_captcha(session: "KSEBSession") -> TransformerCaptcha:
    """Fetch a CAPTCHA image and its unique ID for transformer lookup."""
    try:
        response = session.post(TRANSFORMER_UNIQUE_ID_URL)
        if response.status_code != 200:
            raise KSEBAPIError(
                "Unique ID request failed", status_code=response.status_code,
                response=response.text[:500],
            )
        unique_id = _extract_unique_id(response)
        image_response = session.get(TRANSFORMER_CAPTCHA_URL, params={"uniqId": unique_id})
        if not image_response.content:
            raise KSEBParsingError("Captcha image response was empty", data_type="image")
        return TransformerCaptcha(
            unique_id=unique_id,
            image=image_response.content,
            content_type=image_response.headers.get("Content-Type"),
        )
    except (KSEBAPIError, KSEBParsingError):
        raise
    except Exception as e:
        raise KSEBAPIError(f"Failed to fetch transformer captcha: {e}") from e


def _extract_unique_id(response) -> str:
    """Accept the unique ID returned as plain text, JSON, or HTML input."""
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        for key in ("uniqueId", "uniqId", "unique_id", "id"):
            if data.get(key) is not None:
                return str(data[key]).strip()
    elif isinstance(data, (str, int)):
        value = str(data).strip().strip('"')
        if value:
            return value

    body = response.text.strip()
    if body.isdigit():
        return body
    match = re.search(r"(?:uniqueId|uniqId|unique_id)\s*[=:]\s*[\"']?([A-Za-z0-9_-]+)", body, re.I)
    if match:
        return match.group(1)
    raise KSEBParsingError("Could not find unique ID in response", data_type="JSON/text")


def get_transformers(
    session: "KSEBSession",
    section_code: str,
    section_info: Optional[SectionInfo] = None,
    *,
    captcha_code: str,
    unique_id: str,
) -> list[Transformer]:
    """
    Fetch list of available transformers for a section.

    Args:
        session: KSEBSession instance for making HTTP requests
        section_code: Section code (4-digit code extracted from consumer number)
        section_info: Optional SectionInfo to enrich transformer data with division/subdivision
        captcha_code: User-entered CAPTCHA answer
        unique_id: ID returned with the CAPTCHA challenge

    Returns:
        List of Transformer objects

    Raises:
        KSEBValidationError: If section_code is invalid
        KSEBAPIError: If API request fails
        KSEBParsingError: If response parsing fails
    """
    if not section_code or not isinstance(section_code, str) or len(section_code) != 4:
        raise KSEBValidationError(
            f"Invalid section code format: {section_code}", field="section_code"
        )
    if not isinstance(captcha_code, str) or not captcha_code.strip():
        raise KSEBValidationError("Captcha answer is required", field="captcha_code")
    if not isinstance(unique_id, str) or not unique_id.strip():
        raise KSEBValidationError("Captcha unique ID is required", field="unique_id")

    logger.debug(f"Fetching transformers for section: {section_code}")

    try:
        # Make API request
        response = session.post(
            DTR_AVAILABLE_URL,
            data={"sectionId": section_code, "code": captcha_code.strip(), "uniqueId": unique_id.strip()},
        )

        # Check response status
        if response.status_code != 200:
            raise KSEBAPIError(
                f"Transformer list request failed",
                status_code=response.status_code,
                response=response.text[:500],
            )

        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            raise KSEBParsingError(
                f"Failed to parse transformer API response: {str(e)}", data_type="JSON"
            ) from e

        # The endpoint reports CAPTCHA failures inside an HTTP 200 JSON response.
        if isinstance(data, dict) and data.get("err_flag") == "1":
            message = data.get("messageCd") or "Transformer lookup was rejected"
            raise KSEBAPIError(str(message), response=response.text[:500])

        # Extract transformer list
        if not isinstance(data, dict) or "list" not in data:
            raise KSEBAPIError(
                "Transformer response did not include a list",
                response=response.text[:500],
            )

        transformers_data = data.get("list", [])

        if not isinstance(transformers_data, list):
            raise KSEBParsingError("Transformer list is not a valid list", data_type="JSON")

        # Convert to Transformer objects
        transformers = []

        for dtr_data in transformers_data:
            try:
                transformer = _parse_transformer_data(dtr_data, section_info)
                transformers.append(transformer)
            except (KSEBParsingError, ValueError) as e:
                logger.warning(f"Failed to parse transformer data: {e}")
                continue

        logger.info(f"Retrieved {len(transformers)} transformers for section {section_code}")
        return transformers

    except (KSEBValidationError, KSEBAPIError, KSEBParsingError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching transformers: {e}")
        raise KSEBAPIError(f"Failed to get transformers: {str(e)}") from e


def find_transformer(
    session: "KSEBSession", section_code: str, transformer_name: str,
    *, captcha_code: str, unique_id: str,
) -> Transformer:
    """
    Find a specific transformer by name in a section.

    Args:
        session: KSEBSession instance
        section_code: Section code (4-digit code)
        transformer_name: Name/ID of the transformer

    Returns:
        Transformer object if found

    Raises:
        KSEBValidationError: If inputs are invalid
        KSEBTransformerNotFoundError: If transformer not found
        KSEBAPIError: If API request fails
    """
    if not transformer_name or not isinstance(transformer_name, str):
        raise KSEBValidationError(
            f"Invalid transformer name: {transformer_name}", field="transformer_name"
        )

    # Normalize the name for comparison
    normalized_name = normalize_transformer_name(transformer_name)

    logger.debug(f"Finding transformer: {transformer_name} in section: {section_code}")

    # Get all transformers for the section
    transformers = get_transformers(
        session, section_code, captcha_code=captcha_code, unique_id=unique_id
    )

    # Prefer exact normalized matches, then accept the closest sufficiently similar name.
    for transformer in transformers:
        if normalize_transformer_name(transformer.transformer_name) == normalized_name:
            logger.info(f"Found transformer: {transformer.transformer_name}")
            return transformer

    def similarity(candidate: Transformer) -> float:
        candidate_name = normalize_transformer_name(candidate.transformer_name)
        return SequenceMatcher(None, normalized_name, candidate_name).ratio()

    if transformers:
        best_match = max(transformers, key=similarity)
        score = similarity(best_match)
        if score >= 0.6:
            logger.info("Matched transformer %r to %r (similarity %.2f)", transformer_name, best_match.transformer_name, score)
            return best_match

    # Not found
    raise KSEBTransformerNotFoundError(
        f"Transformer not found: {transformer_name}",
        transformer_name=transformer_name,
        section_code=section_code,
    )


def _parse_transformer_data(data: dict, section_info: Optional[SectionInfo] = None) -> Transformer:
    """
    Parse transformer data from API response.

    Args:
        data: Raw transformer data from API
        section_info: Optional SectionInfo to provide division/subdivision if missing from API response

    Returns:
        Transformer object

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Fields required from API
    required_fields = [
        "transformer_name",
        "allowed_cap",
        "comp_cap",
        "regi",
    ]

    # Fields that may come from API or section_info
    optional_fields = ["division", "sub_division"]

    # Check required fields
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required transformer fields: {missing}")

    try:
        # Get division and sub_division from API data or section_info
        division = data.get("division")
        if not division and section_info:
            division = section_info.division
        division = division or ""

        sub_division = data.get("sub_division")
        if not sub_division and section_info:
            sub_division = section_info.subdivision
        sub_division = sub_division or ""

        # Parse capacity values
        allowed_cap = parse_capacity_value(data["allowed_cap"])
        comp_cap = parse_capacity_value(data["comp_cap"])
        regi = parse_capacity_value(data["regi"])

        # Calculate balance
        balance_available = allowed_cap - (comp_cap + regi)
        balance_available = round(balance_available, 3)

        return Transformer(
            transformer_name=str(data["transformer_name"]).strip(),
            division=str(division).strip(),
            sub_division=str(sub_division).strip(),
            allowed_cap=allowed_cap,
            comp_cap=comp_cap,
            regi=regi,
            balance_available=balance_available,
        )

    except (ValueError, KeyError) as e:
        raise ValueError(f"Failed to parse transformer data: {e}") from e
