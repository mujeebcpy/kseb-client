"""
Data models for KSEB Client SDK.

This module defines dataclasses for representing API responses and results.
These models provide type-safe, structured access to KSEB data.
"""

from dataclasses import dataclass


@dataclass
class SectionInfo:
    """Information about an electrical section."""

    office_code: str
    section: str
    subdivision: str
    subdivision_email: str
    division: str
    division_phone: str
    division_email: str
    phone: str
    email: str

    def __str__(self) -> str:
        return f"SectionInfo(section={self.section}, subdivision={self.subdivision}, division={self.division})"


@dataclass
class BillInfo:
    """Information extracted from a bill PDF."""

    consumer_no: str
    consumer_name: str
    section: str
    dtr: str
    connected_load: str | None = None
    tariff: str | None = None
    phase: str | None = None
    customer_address: str | None = None
    security_deposit: float | None = None
    net_payable: float | None = None

    def __str__(self) -> str:
        return f"BillInfo(consumer_no={self.consumer_no}, consumer_name={self.consumer_name}, dtr={self.dtr})"


@dataclass
class Transformer:
    """Information about a distribution transformer."""

    transformer_name: str
    division: str
    sub_division: str
    allowed_cap: float
    comp_cap: float
    regi: float
    balance_available: float

    def __str__(self) -> str:
        return f"Transformer(name={self.transformer_name}, balance={self.balance_available})"


@dataclass
class GridCapacityResult:
    """Complete grid capacity query result combining section, bill, and transformer info."""

    section: SectionInfo
    bill: BillInfo
    transformer: Transformer

    def __str__(self) -> str:
        return (
            f"GridCapacityResult("
            f"section={self.section.section}, "
            f"consumer={self.bill.consumer_name}, "
            f"balance={self.transformer.balance_available})"
        )
