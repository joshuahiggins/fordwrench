from __future__ import annotations

from fordwrench.uds.dtc import Dtc, decode_dtc
from fordwrench.uds.errors import NegativeResponse


class UdsClient:
    """Minimal UDS client over an adapter exposing set_target() and request()."""

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def set_target(self, request_id: int, response_id: int) -> None:
        self.adapter.set_target(request_id, response_id)

    def _send(self, payload: bytes) -> bytes:
        resp = self.adapter.request(payload)
        if resp and resp[0] == 0x7F:
            service = resp[1] if len(resp) > 1 else 0
            nrc = resp[2] if len(resp) > 2 else 0
            raise NegativeResponse(service=service, nrc=nrc)
        return resp

    def start_session(self, session_type: int = 0x03) -> bytes:
        resp = self._send(bytes([0x10, session_type]))
        return resp

    def read_data_by_identifier(self, did: int) -> bytes:
        resp = self._send(bytes([0x22, (did >> 8) & 0xFF, did & 0xFF]))
        # Positive response: 0x62, DID_hi, DID_lo, <data...>
        return resp[3:]

    def read_dtcs(self, status_mask: int = 0xFF) -> list[Dtc]:
        # 0x19 subfunction 0x02 = reportDTCByStatusMask
        resp = self._send(bytes([0x19, 0x02, status_mask]))
        # Positive: 0x59, 0x02, availabilityMask, then 4-byte records (3 DTC + status)
        records = resp[3:]
        dtcs: list[Dtc] = []
        for i in range(0, len(records) - 3, 4):
            chunk = records[i:i + 4]
            dtcs.append(Dtc(code=decode_dtc(chunk[:3]), status=chunk[3]))
        return dtcs
