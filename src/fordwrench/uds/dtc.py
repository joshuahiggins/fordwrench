from __future__ import annotations

from dataclasses import dataclass

_SYSTEM_LETTERS = ["P", "C", "B", "U"]

STATUS_BITS: list[tuple[int, str]] = [
    (0x01, "testFailed"),
    (0x02, "testFailedThisCycle"),
    (0x04, "pending"),
    (0x08, "confirmed"),
    (0x40, "testNotCompletedThisCycle"),
    (0x80, "warningIndicatorRequested"),
]


@dataclass(frozen=True)
class Dtc:
    code: str
    status: int


def decode_dtc(data: bytes) -> str:
    """Decode a 3-byte UDS DTC into e.g. 'P0420-00'."""
    b0, b1, b2 = data[0], data[1], data[2]
    letter = _SYSTEM_LETTERS[(b0 >> 6) & 0x03]
    code = f"{letter}{(b0 >> 4) & 0x03}{b0 & 0x0F:X}{(b1 >> 4) & 0x0F:X}{b1 & 0x0F:X}"
    return f"{code}-{b2:02X}"


def status_labels(status: int) -> list[str]:
    return [name for bit, name in STATUS_BITS if status & bit]
