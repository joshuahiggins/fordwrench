from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import serial
import typer
from rich.console import Console
from rich.table import Table

from fordwrench.adapter.elm import AdapterError, ElmAdapter
from fordwrench.commands import probe_modules, read_block, read_module_dtcs, sweep_dids
from fordwrench.config import load_modules
from fordwrench.snapshot import capture_snapshot, diff_snapshots, load_snapshot, save_snapshot
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
    session: bool = typer.Option(
        False, "--session", "-s", help="Open an extended diagnostic session (0x10 0x03) first"
    ),
):
    """Read and decode an As-Built block."""
    modules = load_modules()
    if module not in modules:
        console.print(f"[red]Unknown module: {module}[/red]")
        raise typer.Exit(code=1)
    with _hardware_errors():
        uds = build_uds(port)
        block = read_block(uds, modules[module], int(did, 0), extended_session=session)
    console.print(block.render())


@app.command(name="scan-dids")
def scan_dids(
    module: str = typer.Argument(..., help="Module id, e.g. BCM"),
    port: str = typer.Option(..., "--port", help="Serial device"),
    start: str = typer.Option("0xDE00", "--start", help="First DID to try"),
    end: str = typer.Option("0xDEFF", "--end", help="Last DID to try"),
    session: bool = typer.Option(
        False, "--session", "-s", help="Open an extended diagnostic session (0x10 0x03) first"
    ),
):
    """Discover which DIDs a module supports by sweeping a range (read-only)."""
    modules = load_modules()
    if module not in modules:
        console.print(f"[red]Unknown module: {module}[/red]")
        raise typer.Exit(code=1)
    with _hardware_errors():
        uds = build_uds(port)
        hits = sweep_dids(
            uds, modules[module], int(start, 0), int(end, 0), extended_session=session
        )
    if not hits:
        console.print(
            f"No supported DIDs found in {start}–{end} for {module}. "
            "Try a different range (e.g. --start 0xF100 --end 0xF1FF)."
        )
        return
    table = Table(title=f"Supported DIDs — {module}")
    table.add_column("DID")
    table.add_column("Bytes")
    for did, data in hits:
        table.add_row(f"0x{did:04X}", " ".join(f"{b:02X}" for b in data))
    console.print(table)


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


@app.command()
def snapshot(
    port: str = typer.Option(..., "--port", help="Serial device"),
    out: str = typer.Option(
        None, "--out", help="Output path (default: snapshots/snapshot-<time>.json)"
    ),
    start: str = typer.Option("0xDE00", "--start", help="First As-Built DID to sweep"),
    end: str = typer.Option("0xDEFF", "--end", help="Last As-Built DID to sweep"),
):
    """Capture a read-only baseline (DTCs + As-Built) for every known module.

    Session-free and non-destructive — safe to run on all modules."""
    modules = load_modules()
    timestamp = datetime.now().isoformat(timespec="seconds")
    with _hardware_errors():
        uds = build_uds(port)
        snap = capture_snapshot(uds, modules, timestamp, int(start, 0), int(end, 0))
    out_path = (
        Path(out)
        if out
        else Path("snapshots") / f"snapshot-{timestamp.replace(':', '-')}.json"
    )
    save_snapshot(snap, out_path)
    table = Table(title=f"Snapshot — {timestamp}")
    table.add_column("Module")
    table.add_column("DTCs", justify="right")
    table.add_column("As-Built DIDs", justify="right")
    table.add_column("Errors")
    for mod_id, entry in snap["modules"].items():
        table.add_row(
            mod_id,
            str(len(entry["dtcs"])),
            str(len(entry["asbuilt"])),
            "; ".join(entry["errors"]) or "-",
        )
    console.print(table)
    console.print(f"Saved to [bold]{out_path}[/bold]")


@app.command(name="snapshot-diff")
def snapshot_diff(
    old: str = typer.Argument(..., help="Older snapshot JSON"),
    new: str = typer.Argument(..., help="Newer snapshot JSON"),
):
    """Show what changed between two snapshots (DTCs and As-Built)."""
    d = diff_snapshots(load_snapshot(Path(old)), load_snapshot(Path(new)))
    if not d:
        console.print("No changes between snapshots.")
        return
    for mod_id, entry in d.items():
        console.print(f"[bold]{mod_id}[/bold]")
        for code in entry["dtcs_added"]:
            console.print(f"  [red]+ DTC {code}[/red]")
        for code in entry["dtcs_removed"]:
            console.print(f"  [green]- DTC {code} (cleared)[/green]")
        for did, change in entry["asbuilt_changed"].items():
            console.print(f"  [yellow]~ {did}: {change['old']} -> {change['new']}[/yellow]")
        for did in entry["asbuilt_added"]:
            console.print(f"  + {did}")
        for did in entry["asbuilt_removed"]:
            console.print(f"  - {did}")


if __name__ == "__main__":
    app()
