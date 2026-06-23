from __future__ import annotations

from typing import Protocol


class Transport(Protocol):
    """Byte/line pipe to an ELM-style serial adapter."""

    def write_command(self, command: str) -> None: ...

    def read_until_prompt(self, timeout: float = 5.0) -> str: ...

    def close(self) -> None: ...


class MockTransport:
    """In-memory Transport for tests. Maps a sent command to a canned reply."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses: dict[str, str] = responses or {}
        self.sent: list[str] = []
        self._last: str | None = None

    def write_command(self, command: str) -> None:
        self.sent.append(command)
        self._last = command

    def read_until_prompt(self, timeout: float = 5.0) -> str:
        return self.responses.get(self._last or "", "NO DATA\r>")

    def close(self) -> None:
        pass
