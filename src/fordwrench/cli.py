from __future__ import annotations

from contextlib import contextmanager

import serial
import typer
from rich.console import Console
from rich.table import Table

from fordwrench.adapter.elm import AdapterError, ElmAdapter
from fordwrench.commands import probe_modules, read_block, read_module_dtcs
from fordwrench.config import load_modules
from fordwrench.transport.serial_port import SerialTransport, list_serial_ports
from fordwrench.uds.client import UdsClient
from fordwrench.uds.dtc import status_labels
from fordwrench.uds.errors import NegativeResponse

app = typer.Typer(help="Read/write Ford As-Built config and DTCs over OBD-II.")
console = Console()


@contextmanager
def _hardware_errors():
    """Turn hardware/protocol exceptions into clean messages + non-zero exit."""
    try:
        yield
    except NegativeResponse as exc:
        console.print(f"[red]{exc}[/red]")
        if exc.nrc == 0x31:  # requestOutOfRange
            console.print(
                "[yellow]Hint: the module answered but has no such DID. "
                "Check the DID (not the module's CAN ID) against community "
                "As-Built docs.[/yellow]"
            )
        raise typer.Exit(code=1)
    except AdapterError as exc:
        console.print(f"[red]Adapter error: {exc}[/red]")
        raise typer.Exit(code=1)
    except serial.SerialException as exc:
        console.print(f"[red]Serial error: {exc}[/red]")
        console.print("[yellow]Hint: check the --port value and that the adapter is plugged in.[/yellow]")
        raise typer.Exit(code=1)


def build_uds(port: str) -> UdsClient:
    """Build a connected UDS client over a real serial adapter."""
    transport = SerialTransport(port)
    adapter = ElmAdapter(transport)
    adapter.initialize()
    return UdsClient(adapter)


@app.command()
def scan(port: str = typer.Option(None, "--port", help="Serial device. Omit to list ports.")):
    """List serial ports (no --port) or probe modules on the bus (--port)."""
    if not port:
        table = Table(title="Serial ports")
        table.add_column("Device")
        table.add_column("Description")
        for device, description in list_serial_ports():
            table.add_row(device, description)
        console.print(table)
        return

    with _hardware_errors():
        uds = build_uds(port)
        responders = probe_modules(uds.adapter, load_modules())
    table = Table(title="Responding modules")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Request")
    table.add_column("Response")
    for m in responders:
        table.add_row(m.id, m.name, f"0x{m.request_id:03X}", f"0x{m.response_id:03X}")
    console.print(table)


@app.command()
def read(
    module: str = typer.Argument(..., help="Module id, e.g. BCM"),
    did: str = typer.Argument(..., help="Data identifier, e.g. 0xDE00"),
    port: str = typer.Option(..., "--port", help="Serial device"),
):
    """Read and decode an As-Built block."""
    modules = load_modules()
    if module not in modules:
        console.print(f"[red]Unknown module: {module}[/red]")
        raise typer.Exit(code=1)
    with _hardware_errors():
        uds = build_uds(port)
        block = read_block(uds, modules[module], int(did, 0))
    console.print(block.render())


@app.command()
def dtc(
    module: str = typer.Argument(..., help="Module id, e.g. BCM"),
    port: str = typer.Option(..., "--port", help="Serial device"),
):
    """Read diagnostic trouble codes from a module."""
    modules = load_modules()
    if module not in modules:
        console.print(f"[red]Unknown module: {module}[/red]")
        raise typer.Exit(code=1)
    with _hardware_errors():
        uds = build_uds(port)
        codes = read_module_dtcs(uds, modules[module])
    if not codes:
        console.print(f"No DTCs reported by {module}.")
        return
    table = Table(title=f"DTCs — {module}")
    table.add_column("Code")
    table.add_column("Status")
    for d in codes:
        table.add_row(d.code, ", ".join(status_labels(d.status)) or f"0x{d.status:02X}")
    console.print(table)


if __name__ == "__main__":
    app()
