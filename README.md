# fordwrench

Open-source CLI for reading (and, in later milestones, writing) Ford module
configuration ("As-Built data") over the OBD-II port, plus reading diagnostic
trouble codes. Cross-platform: **macOS and Windows**.

> **Scope today:** read-only — `scan`, `read`, `dtc`. Writing config and the
> recipe/seed-key features land in later milestones.

> **Legal & safety:** Use only on a vehicle you own. Reading is safe; the
> upcoming write features can damage modules if misused. This project contains
> no code extracted from FORScan or any other proprietary tool.

## Requirements

- Python 3.11+
- An OBDLink EX (or other STN-based, CAN-FD-capable serial adapter)
- A 2021 Bronco is the reference vehicle; other Fords may work via the module
  registry.

## Install

```bash
git clone <repo-url>
cd fordwrench
python3 -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

## Find your adapter's serial port

```bash
fordwrench scan
```

- macOS: a `/dev/tty.usbserial-*` device.
- Windows: a `COMx` device. Install the FTDI VCP driver if the EX does not
  appear.

## Usage

Probe which modules respond on the bus:
```bash
fordwrench scan --port /dev/tty.usbserial-1420     # or COM3 on Windows
```

Read an As-Built block:
```bash
fordwrench read BCM 0xDE00 --port /dev/tty.usbserial-1420
```

Read diagnostic trouble codes:
```bash
fordwrench dtc BCM --port /dev/tty.usbserial-1420
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

All protocol logic is tested against an in-memory mock transport/adapter, so the
suite runs with no vehicle attached.
