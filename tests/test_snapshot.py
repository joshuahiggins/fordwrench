from fordwrench.adapter.elm import MockAdapter
from fordwrench.config import Module
from fordwrench.snapshot import capture_snapshot, diff_snapshots, load_snapshot, save_snapshot
from fordwrench.uds.client import UdsClient


def _modules():
    return {
        "BCM": Module("BCM", "Body Control Module", 0x726, 0x72E, "HS-CAN-FD", 0x01),
        "ABS": Module("ABS", "Anti-lock Brake System", 0x760, 0x768, "HS-CAN-FD", 0x01),
    }


def test_capture_snapshot_collects_dtcs_and_asbuilt_per_module():
    def handler(target, payload):
        if payload[0] == 0x19:  # ReadDTC
            if target == 0x726:
                return bytes([0x59, 0x02, 0xFF, 0x04, 0x20, 0x00, 0x08])
            return bytes([0x59, 0x02, 0xFF])  # ABS: no DTCs
        if payload[0] == 0x22:  # ReadDataByIdentifier
            did = (payload[1] << 8) | payload[2]
            if target == 0x726 and did == 0xDE02:
                return bytes([0x62, 0xDE, 0x02, 0x01])
            return bytes([0x7F, 0x22, 0x31])  # requestOutOfRange
        return bytes([0x7F, payload[0], 0x11])

    uds = UdsClient(MockAdapter(handler))
    snap = capture_snapshot(uds, _modules(), "2026-06-23T12:00:00", 0xDE00, 0xDE03)

    assert snap["timestamp"] == "2026-06-23T12:00:00"
    bcm = snap["modules"]["BCM"]
    assert bcm["dtcs"] == [{"code": "P0420-00", "status": 0x08}]
    assert bcm["asbuilt"] == {"0xDE02": "01"}
    assert snap["modules"]["ABS"]["dtcs"] == []
    assert snap["modules"]["ABS"]["asbuilt"] == {}


def test_capture_snapshot_never_opens_a_session():
    sent = []

    def handler(target, payload):
        sent.append(payload[0])
        if payload[0] == 0x19:
            return bytes([0x59, 0x02, 0xFF])
        return bytes([0x7F, 0x22, 0x31])

    uds = UdsClient(MockAdapter(handler))
    capture_snapshot(uds, _modules(), "t", 0xDE00, 0xDE01)
    assert 0x10 not in sent  # DiagnosticSessionControl must never be sent


def test_diff_snapshots_reports_dtc_and_asbuilt_changes():
    old = {"modules": {"ABS": {"dtcs": [], "asbuilt": {"0xDE02": "00", "0xDE03": "AA"}}}}
    new = {
        "modules": {
            "ABS": {
                "dtcs": [{"code": "C1234-00", "status": 8}],
                "asbuilt": {"0xDE02": "01", "0xDE04": "FF"},
            }
        }
    }
    d = diff_snapshots(old, new)
    assert d["ABS"]["dtcs_added"] == ["C1234-00"]
    assert d["ABS"]["asbuilt_changed"] == {"0xDE02": {"old": "00", "new": "01"}}
    assert d["ABS"]["asbuilt_added"] == ["0xDE04"]
    assert d["ABS"]["asbuilt_removed"] == ["0xDE03"]


def test_diff_snapshots_empty_when_identical():
    snap = {"modules": {"BCM": {"dtcs": [], "asbuilt": {"0xDE02": "01"}}}}
    assert diff_snapshots(snap, snap) == {}


def test_save_and_load_round_trip(tmp_path):
    snap = {"timestamp": "t", "modules": {"BCM": {"dtcs": [], "asbuilt": {"0xDE02": "01"}}}}
    path = tmp_path / "snapshots" / "snap.json"
    save_snapshot(snap, path)
    assert load_snapshot(path) == snap
