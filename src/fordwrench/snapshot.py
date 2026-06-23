"""Read-only vehicle snapshots: capture DTCs + As-Built data for every module,
save to JSON, and diff two snapshots to see what changed.

Snapshots use only non-destructive services (0x19 DTC read, 0x22 As-Built read)
and never open a diagnostic session, so they are safe to run against any module
including safety/drivetrain modules.
"""
from __future__ import annotations

import json
from pathlib import Path

from fordwrench.adapter.elm import AdapterError
from fordwrench.commands import read_module_dtcs, sweep_dids
from fordwrench.config import Module
from fordwrench.uds.client import UdsClient
from fordwrench.uds.errors import NegativeResponse


def capture_snapshot(
    uds: UdsClient,
    modules: dict[str, Module],
    timestamp: str,
    did_start: int = 0xDE00,
    did_end: int = 0xDEFF,
) -> dict:
    """Capture DTCs and the readable As-Built DIDs for every module.

    Failures on a single module are recorded per-module and do not abort the
    whole snapshot. No diagnostic session is ever opened (safe on all modules).
    """
    snapshot: dict = {"timestamp": timestamp, "modules": {}}
    for mod_id, module in modules.items():
        entry: dict = {
            "name": module.name,
            "request_id": f"0x{module.request_id:03X}",
            "response_id": f"0x{module.response_id:03X}",
            "dtcs": [],
            "asbuilt": {},
            "errors": [],
        }
        try:
            entry["dtcs"] = [
                {"code": d.code, "status": d.status} for d in read_module_dtcs(uds, module)
            ]
        except (NegativeResponse, AdapterError) as exc:
            entry["errors"].append(f"dtc: {exc}")
        try:
            hits = sweep_dids(uds, module, did_start, did_end)
            entry["asbuilt"] = {f"0x{did:04X}": data.hex().upper() for did, data in hits}
        except (NegativeResponse, AdapterError) as exc:
            entry["errors"].append(f"asbuilt: {exc}")
        snapshot["modules"][mod_id] = entry
    return snapshot


def diff_snapshots(old: dict, new: dict) -> dict:
    """Compare two snapshots; return only the modules that changed.

    Per changed module: dtcs_added/removed (by code) and asbuilt
    changed/added/removed (by DID)."""
    diff: dict = {}
    old_mods = old.get("modules", {})
    new_mods = new.get("modules", {})
    for mod_id in sorted(set(old_mods) | set(new_mods)):
        o = old_mods.get(mod_id, {})
        n = new_mods.get(mod_id, {})
        o_dtc = {d["code"] for d in o.get("dtcs", [])}
        n_dtc = {d["code"] for d in n.get("dtcs", [])}
        o_ab = o.get("asbuilt", {})
        n_ab = n.get("asbuilt", {})
        entry = {
            "dtcs_added": sorted(n_dtc - o_dtc),
            "dtcs_removed": sorted(o_dtc - n_dtc),
            "asbuilt_changed": {
                did: {"old": o_ab[did], "new": n_ab[did]}
                for did in sorted(set(o_ab) & set(n_ab))
                if o_ab[did] != n_ab[did]
            },
            "asbuilt_added": sorted(set(n_ab) - set(o_ab)),
            "asbuilt_removed": sorted(set(o_ab) - set(n_ab)),
        }
        if any(entry.values()):
            diff[mod_id] = entry
    return diff


def save_snapshot(snapshot: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2))


def load_snapshot(path: Path) -> dict:
    return json.loads(Path(path).read_text())
