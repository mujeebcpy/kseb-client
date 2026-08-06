"""
Transformer information retrieval from KSEB endpoints.

This module handles fetching and matching transformer details.
"""

import logging
from typing import TYPE_CHECKING, Optional

from .constants import DTR_AVAILABLE_URL
from .exceptions import KSEBAPIError, KSEBParsingError, KSEBTransformerNotFoundError, KSEBValidationError
from .models import SectionInfo, Transformer
from .utils import extract_section_code, normalize_transformer_name, parse_capacity_value, validate_consumer_no

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def get_transformers(session: "KSEBSession", section_code: str, section_info: Optional[SectionInfo] = None) -> list[Transformer]:
    """
    Fetch list of available transformers for a section.

    Args:
        session: KSEBSession instance for making HTTP requests
        section_code: Section code (4-digit code extracted from consumer number)
        section_info: Optional SectionInfo to enrich transformer data with division/subdivision

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

    logger.debug(f"Fetching transformers for section: {section_code}")

    try:
        # Make API request
        response = session.post(DTR_AVAILABLE_URL, data={"sectionId": section_code})

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

        # Extract transformer list
        if "list" not in data:
            logger.warning(f"No transformers found for section: {section_code}")
            return []

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


def find_transformer(session: "KSEBSession", section_code: str, transformer_name: str) -> Transformer:
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
    transformers = get_transformers(session, section_code)

    # Search for matching transformer
    for transformer in transformers:
        if normalize_transformer_name(transformer.transformer_name) == normalized_name:
            logger.info(f"Found transformer: {transformer.transformer_name}")
            return transformer

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
