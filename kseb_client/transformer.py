"""
Transformer information retrieval from KSEB endpoints.

This module handles fetching the transformer (DTR) capacity for a consumer.
"""

import logging
from typing import TYPE_CHECKING, Optional

from .constants import DTR_AVAILABLE_URL, FORM_FIELD_DTR_CONSUMER_NO, FORM_FIELD_TURNSTILE
from .exceptions import KSEBAPIError, KSEBParsingError, KSEBTurnstileError, KSEBValidationError
from .models import SectionInfo, Transformer
from .utils import parse_capacity_value, validate_consumer_no

if TYPE_CHECKING:
    from .session import KSEBSession

logger = logging.getLogger(__name__)


def get_transformer(
    session: "KSEBSession",
    consumer_no: str,
    *,
    turnstile_token: str,
    section_info: Optional[SectionInfo] = None,
) -> Transformer:
    """
    Fetch the transformer serving a consumer, with its solar capacity.

    KSEB protects this endpoint with Cloudflare Turnstile. The token must come
    from a person completing the Turnstile check on the KSEB website, and it can
    be used only once.

    Args:
        session: KSEBSession instance for making HTTP requests
        consumer_no: KSEB consumer number (13 digits)
        turnstile_token: ``cf-turnstile-response`` value from the Turnstile check
        section_info: Optional SectionInfo to fill in division/subdivision

    Returns:
        Transformer object

    Raises:
        KSEBValidationError: If inputs are invalid
        KSEBTurnstileError: If KSEB rejects the Turnstile token
        KSEBAPIError: If the API request fails
        KSEBParsingError: If response parsing fails
    """
    if not validate_consumer_no(consumer_no):
        raise KSEBValidationError(f"Invalid consumer number format: {consumer_no}", field="consumer_no")
    if not isinstance(turnstile_token, str) or not turnstile_token.strip():
        raise KSEBValidationError(
            "Turnstile verification is required: complete the Cloudflare check first",
            field="turnstile_token",
        )

    logger.debug(f"Fetching transformer for consumer: {consumer_no}")

    try:
        response = session.post(
            DTR_AVAILABLE_URL,
            data={
                FORM_FIELD_DTR_CONSUMER_NO: consumer_no,
                FORM_FIELD_TURNSTILE: turnstile_token.strip(),
            },
        )

        if response.status_code != 200:
            raise KSEBAPIError(
                "Transformer request failed",
                status_code=response.status_code,
                response=response.text[:500],
            )

        try:
            data = response.json()
        except Exception as e:
            raise KSEBParsingError(
                f"Failed to parse transformer API response: {str(e)}", data_type="JSON"
            ) from e

        if not isinstance(data, dict):
            raise KSEBParsingError("Transformer response is not a JSON object", data_type="JSON")

        # The endpoint reports failures inside an HTTP 200 JSON response.
        if str(data.get("err_flag")) != "0":
            message = str(data.get("disp_msg") or data.get("messageCd") or "Transformer lookup was rejected")
            if "verification" in message.lower() or "turnstile" in message.lower():
                raise KSEBTurnstileError(
                    f"Turnstile verification failed: {message}. Complete the Cloudflare check again."
                )
            raise KSEBAPIError(message, response=response.text[:500])

        dtr = data.get("dtr")
        if not isinstance(dtr, dict):
            raise KSEBAPIError("Transformer response did not include DTR details", response=response.text[:500])

        try:
            transformer = _parse_transformer_data(dtr, data.get("ason"), section_info)
        except ValueError as e:
            raise KSEBParsingError(str(e), data_type="JSON") from e

        logger.info(f"Retrieved transformer {transformer.transformer_name} for consumer {consumer_no}")
        return transformer

    except (KSEBValidationError, KSEBAPIError, KSEBParsingError, KSEBTurnstileError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching transformer: {e}")
        raise KSEBAPIError(f"Failed to get transformer: {str(e)}") from e


def _parse_transformer_data(
    data: dict, as_on: Optional[str] = None, section_info: Optional[SectionInfo] = None
) -> Transformer:
    """
    Parse the ``dtr`` object from the API response.

    Args:
        data: Raw ``dtr`` data from API
        as_on: ``ason`` date from the API response
        section_info: Optional SectionInfo to provide division/subdivision

    Returns:
        Transformer object

    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = ["transformer_name", "available_cap", "connected_cap", "balance_cap"]

    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required transformer fields: {missing}")

    try:
        division = data.get("division") or (section_info.division if section_info else "") or ""
        sub_division = data.get("sub_division") or (section_info.subdivision if section_info else "") or ""

        capacity = data.get("capacity")

        return Transformer(
            transformer_name=str(data["transformer_name"]).strip(),
            division=str(division).strip(),
            sub_division=str(sub_division).strip(),
            allowed_cap=parse_capacity_value(data["available_cap"]),
            comp_cap=parse_capacity_value(data["connected_cap"]),
            regi=0.0,
            balance_available=parse_capacity_value(data["balance_cap"]),
            capacity_kva=parse_capacity_value(capacity) if capacity not in (None, "") else None,
            as_on=str(as_on).strip() if as_on else None,
        )

    except (ValueError, KeyError) as e:
        raise ValueError(f"Failed to parse transformer data: {e}") from e
