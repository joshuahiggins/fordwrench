from __future__ import annotations

from typing import Callable

from fordwrench.transport.base import Transport

_ERROR_TOKENS = ("NO DATA", "CAN ERROR", "BUFFER FULL", "STOPPED", "UNABLE TO CONNECT", "?")


class AdapterError(Exception):
    """Raised when the adapter reports an error instead of a usable response."""


class ElmAdapter:
    """Drives an ELM327/STN serial adapter (e.g. OBDLink EX).

    NOTE (hardware bring-up, Task 4): DEFAULT_INIT selects a baseline CAN
    configuration. The exact protocol/CAN-FD ST command for the 2021 Bronco
    buses is confirmed empirically in Task 4 and updated here.
    """

    # Headers off (ATH0) so responses are bare assembled UDS payloads; the RX
    # filter set in set_target restricts traffic to the target module.
    DEFAULT_INIT = ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP6"]

    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    def _command(self, cmd: str) -> str:
        self.transport.write_command(cmd)
        resp = self.transport.read_until_prompt()
        upper = resp.upper()
        if "?" in upper or "ERROR" in upper:
            raise AdapterError(f"command failed: {cmd} -> {resp!r}")
        return resp

    def initialize(self) -> None:
        for cmd in self.DEFAULT_INIT:
            self._command(cmd)

    def set_target(self, request_id: int, response_id: int) -> None:
        self._command(f"ATSH{request_id:03X}")
        self._command(f"ATCRA{response_id:03X}")

    def request(self, payload: bytes, timeout: float = 5.0) -> bytes:
        command = payload.hex().upper()
        self.transport.write_command(command)
        raw = self.transport.read_until_prompt(timeout)
        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> bytes:
        chunks: list[str] = []
        for line in raw.replace("\r", "\n").splitlines():
            line = line.strip()
            if not line or line == ">":
                continue
            if any(tok in line.upper() for tok in _ERROR_TOKENS):
                raise AdapterError(line)
            # Strip an ELM multi-line index prefix like "0:" or "1:".
            if ":" in line[:3]:
                line = line.split(":", 1)[1]
            chunks.append(line.replace(" ", ""))
        hexstr = "".join(chunks)
        if not hexstr:
            raise AdapterError("empty response")
        return bytes.fromhex(hexstr)


class MockAdapter:
    """Adapter test double. Delegates request() to a handler(target, payload)."""

    def __init__(self, handler: Callable[[int | None, bytes], bytes]) -> None:
        self.handler = handler
        self.target: int | None = None
        self.requests: list[tuple[int | None, bytes]] = []

    def initialize(self) -> None:
        pass

    def set_target(self, request_id: int, response_id: int) -> None:
        self.target = request_id

    def request(self, payload: bytes, timeout: float = 5.0) -> bytes:
        self.requests.append((self.target, bytes(payload)))
        return self.handler(self.target, bytes(payload))
