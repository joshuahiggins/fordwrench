# fordwrench

Open-source CLI for reading (and, in later milestones, writing) Ford module
configuration ("As-Built data") over the OBD-II port, plus reading diagnostic
trouble codes. Cross-platform: **macOS and Windows**.

> **Scope today:** read-only — `scan`, `scan-dids`, `read`, `dtc`, `snapshot`,
> `snapshot-diff`. Writing config and the recipe/seed-key features land in later
> milestones.

> **Not a FORScan clone.** Contains no code or data extracted from FORScan or any
> other proprietary tool.

## ⚠️ Safety

Use only on a vehicle you own.

- **Reading is safe.** `read`, `dtc`, `scan`, `scan-dids` (without `--session`),
  and `snapshot` use only non-destructive UDS reads.
- **Avoid `--session` on safety/drivetrain modules** (ABS, airbag/RCM, power
  steering/PSCM, all-terrain/ATCM). Opening a diagnostic session on these with
  the key on can knock them into a network-wide fault state (e.g. 4x4 / drive
  modes becoming unavailable) that requires a capable tool like FORScan to clear.
- fordwrench **cannot clear trouble codes** — keep FORScan (or a Ford-capable
  scanner) available as a recovery backstop before any session work.
- Writing config is not implemented yet; when it is, it will be gated behind
  explicit confirmation and a backup/verify safety flow.

## Requirements

- Python 3.11+
- An OBDLink EX (or other STN-based, CAN-FD-capable serial adapter)
- A 2021 Bronco is the reference vehicle; other Fords may work via the module
  registry (`src/fordwrench/data/modules.yaml`).

## Install

```bash
git clone https://github.com/joshuahiggins/fordwrench
cd fordwrench
python3 -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

## Find your adapter's serial port

```bash
fordwrench scan
```

- macOS: a `/dev/cu.usbserial-*` (or `/dev/tty.usbserial-*`) device.
- Windows: a `COMx` device. Install the FTDI VCP driver if the EX does not
  appear.

## Usage

Probe which modules respond on the bus:
```bash
fordwrench scan --port /dev/cu.usbserial-XXXX     # or COMx on Windows
```

Discover which DIDs a module supports (read-only range sweep):
```bash
fordwrench scan-dids BCM --port /dev/cu.usbserial-XXXX
```

Read and decode an As-Built block:
```bash
fordwrench read BCM 0xDE00 --port /dev/cu.usbserial-XXXX
```

Read diagnostic trouble codes:
```bash
fordwrench dtc ABS --port /dev/cu.usbserial-XXXX
```

Capture a read-only baseline of every module (DTCs + As-Built), then diff later:
```bash
fordwrench snapshot --port /dev/cu.usbserial-XXXX
fordwrench snapshot-diff snapshots/<old>.json snapshots/<new>.json
```
Snapshots are written to `snapshots/` (gitignored — they contain your VIN).

`--session` / `-s` (on `read` and `scan-dids`) opens an extended diagnostic
session first — see **Safety** before using it on any safety module.

## Development

```bash
pip install -e ".[dev]"
pytest
```

All protocol logic is tested against an in-memory mock transport/adapter, so the
full suite runs with no vehicle attached.
