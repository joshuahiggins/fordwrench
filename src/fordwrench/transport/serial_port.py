from __future__ import annotations

import serial
from serial.tools.list_ports import comports


def list_serial_ports() -> list[tuple[str, str]]:
    """Return (device, description) for every serial port the OS reports.

    Works the same on macOS (/dev/tty.*) and Windows (COMx); the only
    difference is the device naming, which the OS provides directly.
    """
    return [(p.device, p.description) for p in comports()]


class SerialTransport:
    """pyserial-backed Transport. Exercised on hardware, not in unit tests."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0) -> None:
        self.timeout = timeout
        self._ser = serial.Serial(port, baudrate, timeout=timeout)

    def write_command(self, command: str) -> None:
        self._ser.reset_input_buffer()
        self._ser.write((command + "\r").encode("ascii"))

    def read_until_prompt(self, timeout: float = 5.0) -> str:
        raw = self._ser.read_until(b">")
        return raw.decode("ascii", errors="replace")

    def close(self) -> None:
        self._ser.close()
