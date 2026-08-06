"""
Utility functions for KSEB Client SDK.

This module contains helper functions and utilities used throughout the SDK.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_consumer_no(consumer_no: str) -> bool:
    """
    Validate KSEB consumer number format.

    Args:
        consumer_no: Consumer number to validate

    Returns:
        True if valid, False otherwise
    """
    if not consumer_no or not isinstance(consumer_no, str):
        return False

    # KSEB consumer numbers are typically 13 digits
    consumer_no = consumer_no.strip()
    return len(consumer_no) == 13 and consumer_no.isdigit()


def validate_mobile(mobile: str) -> bool:
    """
    Validate Indian mobile number format.

    Args:
        mobile: Mobile number to validate

    Returns:
        True if valid, False otherwise
    """
    if not mobile or not isinstance(mobile, str):
        return False

    mobile = mobile.strip()
    # Indian mobile numbers are 10 digits
    return len(mobile) == 10 and mobile.isdigit()


def extract_section_code(consumer_no: str) -> str:
    """
    Extract section code from consumer number.

    The section code is typically extracted from a specific position in the consumer number.
    Based on the existing script, it appears to be positions 2-6 (0-indexed).

    Args:
        consumer_no: Consumer number (13 digits)

    Returns:
        Section code (4 digits)
    """
    if not validate_consumer_no(consumer_no):
        raise ValueError(f"Invalid consumer number: {consumer_no}")

    return consumer_no[2:6]


def normalize_transformer_name(name: str) -> str:
    """
    Normalize transformer name for comparison.

    Args:
        name: Transformer name to normalize

    Returns:
        Normalized transformer name
    """
    if not name:
        return ""

    # Strip whitespace and convert to uppercase for case-insensitive comparison
    return name.strip().upper()


def parse_capacity_value(value: str | float) -> float:
    """
    Parse capacity value (handles strings with units).

    Args:
        value: Capacity value as string or float

    Returns:
        Capacity value as float

    Raises:
        ValueError: If value cannot be parsed
    """
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        raise ValueError(f"Cannot parse capacity value: {value}")

    value = value.strip()

    # Try to extract the numeric part
    import re

    match = re.match(r"^([\d.]+)", value)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    try:
        return float(value)
    except ValueError as e:
        raise ValueError(f"Cannot parse capacity value: {value}") from e


def calculate_balance_available(allowed_cap: float | str, comp_cap: float | str, regi: float | str) -> float:
    """
    Calculate available balance capacity.

    Formula: balance_available = allowed_cap - (comp_cap + regi)

    Args:
        allowed_cap: Allowed capacity
        comp_cap: Completed capacity
        regi: Registered capacity

    Returns:
        Available balance
    """
    try:
        allowed = parse_capacity_value(allowed_cap)
        comp = parse_capacity_value(comp_cap)
        reg = parse_capacity_value(regi)

        balance = allowed - (comp + reg)
        return round(balance, 3)
    except ValueError as e:
        logger.error(f"Failed to calculate balance: {e}")
        raise


def create_transformer_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create transformer data dict from API response and calculate balance.

    Args:
        data: Transformer data from API response

    Returns:
        Processed transformer data with calculated balance_available
    """
    try:
        balance = calculate_balance_available(
            data.get("allowed_cap", "0"),
            data.get("comp_cap", "0"),
            data.get("regi", "0"),
        )
        processed = dict(data)
        processed["balance_available"] = balance
        return processed
    except Exception as e:
        logger.error(f"Failed to process transformer data: {e}")
        # Return original data if processing fails
        return data
