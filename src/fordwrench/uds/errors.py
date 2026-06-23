from __future__ import annotations

NRC_NAMES: dict[int, str] = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x22: "conditionsNotCorrect",
    0x24: "requestSequenceError",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceedNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x7E: "subFunctionNotSupportedInActiveSession",
    0x7F: "serviceNotSupportedInActiveSession",
}


class NegativeResponse(Exception):
    """A UDS negative response (0x7F service NRC)."""

    def __init__(self, service: int, nrc: int) -> None:
        self.service = service
        self.nrc = nrc
        name = NRC_NAMES.get(nrc, "unknown")
        super().__init__(f"UDS negative response: service=0x{service:02X} nrc=0x{nrc:02X} ({name})")
