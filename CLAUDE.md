# fordwrench — project guide for Claude

`fordwrench` is a small, open-source, cross-platform (macOS + Windows) Python CLI
for reading — and eventually writing — Ford module configuration ("As-Built
data") over the OBD-II port, plus reading diagnostic trouble codes (DTCs).
Reference vehicle: a **2021 Ford Bronco**, via an **OBDLink EX** adapter.

It is **not** a FORScan clone and contains **no** code or data extracted from
FORScan or any proprietary tool. The write path (later milestone) derives module
security access legitimately from the owner's own vehicle.

## ⚠️ SAFETY — read before any vehicle interaction

**NEVER open a diagnostic session (UDS `0x10`) on a safety/drivetrain module
with the key on.** Doing this on the ABS (`0x760`) once knocked the All-Terrain
Control Module / 4WD modules into a network-wide lost-communication state —
"Check 4x4", "Drive Mode Not Available", no shift-to-Drive — that a battery reset
and drive cycle did **not** clear. It required **FORScan's clear-all** to
recover. Treat the airbag (RCM), power steering (PSCM), ABS, and ATCM as
off-limits for sessions.

Rules:
- **Plain reads are safe**: `0x22` (ReadDataByIdentifier) and `0x19` (ReadDTC)
  with **no session** never caused trouble. The `snapshot` command is
  deliberately session-free.
- The `--session` flag on `read`/`scan-dids` sends `0x10 0x03` — only use it on
  non-safety modules, and flag the risk to the user first.
- **fordwrench cannot clear DTCs** (no `0x14`). Keep **FORScan on the Windows
  box as the recovery backstop** before any session/write work.
- **No writes** (`0x2E`) happen without an explicit user go-ahead AND a tested
  safety harness (backup → dry-run → verify → restore, session keep-alive,
  safety-module guardrails). That harness does not exist yet.

## Architecture

Single-purpose layers, each depending only on the one below, fully unit-testable
against a mock transport (no vehicle needed):

```
cli.py            typer commands + rich output; build_uds() seam; _hardware_errors()
commands.py       probe_modules, read_block, read_module_dtcs, sweep_dids
snapshot.py       capture_snapshot, diff_snapshots, save/load (read-only baseline)
asbuilt/block.py  AsBuiltBlock (read-side model)
uds/              client.py (0x10/0x22/0x2E machinery, 0x19), dtc.py, errors.py
adapter/elm.py    ElmAdapter (ELM/STN init, set_target, ISO-TP multi-frame parse), MockAdapter
transport/        base.py (Transport + MockTransport), serial_port.py (pyserial + port discovery)
config.py + data/modules.yaml   module registry
```

Key seams: `MockTransport` (canned serial text) and `MockAdapter`
(`handler(target, payload)`) make the whole stack testable. The ELM parser
handles ISO-TP multi-frame (drops the length-header line, truncates trailing
padding).

## Commands

```
fordwrench scan [--port P]                 list serial ports (no --port) or probe modules
fordwrench scan-dids MOD --port P [--start 0xDE00 --end 0xDEFF] [--session]
fordwrench read MOD DID --port P [--session]
fordwrench dtc MOD --port P
fordwrench snapshot --port P [--out F]      read-only baseline (DTCs+As-Built, all modules)
fordwrench snapshot-diff OLD.json NEW.json  what changed between two snapshots
```
`--session`/`-s` opens an extended diagnostic session first (see SAFETY).

## Modules (data/modules.yaml)

Registry maps id → CAN request/response IDs. Present: BCM (0x726/0x72E),
IPC (0x720/0x728), APIM (0x7D0/0x7D8), ABS (0x760/0x768). IDs/levels confirmed or
pending per real-vehicle testing.

## Repo conventions

- **Public repo** (`github.com/joshuahiggins/fordwrench`). Keep VIN, the
  adapter's device serial, and any vehicle-specific captured values OUT of
  committed files — they belong in local memory / gitignored dirs only.
- **Do NOT add `Co-Authored-By: Claude` trailers** to commits (stripped from
  history by request).
- `docs/superpowers/` (design spec + plans) is **gitignored / local-only**.
- `snapshots/` is **gitignored** (snapshots contain the VIN).
- Commit email stays `hello@joshuahiggins.com`.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest            # ~50 tests, all run with no vehicle attached
```
Follow TDD (test first), frequent focused commits, conventional-commit messages.

## Status & next steps

- **Done:** read-only foundation (`scan`/`read`/`dtc`), `scan-dids`, `snapshot`/
  `snapshot-diff`, ISO-TP multi-frame parsing, clean CLI error handling. Validated
  on the real Bronco (reads work over CAN-FD).
- **Next (safe, offline, highest-leverage):** crack the Ford As-Built **checksum**
  using the owner's official Ford As-Built `.ab` export (XML; labels
  `MMM-BB-LL`; the **last byte of each block is its checksum**). This is the
  brick-risk gate for every future write — solvable on the laptop, no vehicle.
  First attempts (whole-block sum/XOR) failed; it's likely per-line and folds in
  the address — needs a methodical offline spike.
- **Then:** `.ab` importer (Ford data as the baseline to diff against), then
  **Plan 2** (write/safety flow + security access) — only with the safety harness
  above and explicit sign-off.
- **Open unknown:** the FORScan As-Built address (`MMM-BB-LL`) → UDS DID mapping
  for *writing* is not yet solved. Note: bare per-DID `0x22` reads (e.g. BCM
  `0xDE02`) return short un-checksummed values and are NOT the same as the
  multi-byte checksummed As-Built blocks.

Design docs (local only): `docs/superpowers/specs/` and `docs/superpowers/plans/`.
Feature data sources: bronco6g FORScan subforum + a community Bronco As-Built
spreadsheet. Example targets (public community info): disable double-honk =
BCM `726-63-02` (clear the marked nibble); Sport/GOAT mode = ABS `760-04-03`
(set marked nibble, e.g. `B` for Sport).
