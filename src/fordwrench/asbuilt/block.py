from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AsBuiltBlock:
    """An As-Built configuration block read via UDS 0x22.

    The trailing byte is provisionally treated as the block checksum; this is
    confirmed against real reads in Task 11 before any write path relies on it.
    """

    module_id: int
    did: int
    raw: bytes

    @property
    def label(self) -> str:
        return f"{self.module_id:03X}-{self.did:04X}"

    @property
    def data(self) -> bytes:
        return self.raw[:-1]

    @property
    def checksum(self) -> int:
        return self.raw[-1]

    def byte(self, offset: int) -> int:
        return self.raw[offset]

    def render(self) -> str:
        hex_bytes = " ".join(f"{b:02X}" for b in self.raw)
        return f"{self.label}: {hex_bytes}"
