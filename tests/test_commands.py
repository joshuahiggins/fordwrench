from fordwrench.adapter.elm import AdapterError, MockAdapter
from fordwrench.config import Module
from fordwrench.commands import probe_modules, read_block, read_module_dtcs, sweep_dids
from fordwrench.uds.client import UdsClient


def _modules():
    return {
        "BCM": Module("BCM", "Body Control Module", 0x726, 0x72E, "HS-CAN-FD", 0x01),
        "IPC": Module("IPC", "Instrument Panel Cluster", 0x720, 0x728, "HS-CAN-FD", 0x01),
    }


def test_probe_modules_returns_only_responders():
    def handler(target, payload):
        if target == 0x726:
            return bytes([0x7E, 0x00])
        raise AdapterError("NO DATA")

    responders = probe_modules(MockAdapter(handler), _modules())
    assert [m.id for m in responders] == ["BCM"]


def test_read_block_sets_target_and_returns_block():
    def handler(target, payload):
        assert target == 0x726
        return bytes([0x62, 0xDE, 0x00, 0x04, 0x01, 0x00, 0x17])

    uds = UdsClient(MockAdapter(handler))
    block = read_block(uds, _modules()["BCM"], 0xDE00)
    assert block.label == "726-DE00"
    assert block.raw == bytes([0x04, 0x01, 0x00, 0x17])


def test_read_module_dtcs_targets_module():
    def handler(target, payload):
        assert target == 0x720
        return bytes([0x59, 0x02, 0xFF, 0x04, 0x20, 0x00, 0x08])

    uds = UdsClient(MockAdapter(handler))
    dtcs = read_module_dtcs(uds, _modules()["IPC"])
    assert [d.code for d in dtcs] == ["P0420-00"]


def test_sweep_dids_returns_only_supported_dids():
    def handler(target, payload):
        did = (payload[1] << 8) | payload[2]
        if did == 0xDE01:
            return bytes([0x62, 0xDE, 0x01, 0xAA, 0xBB])
        return bytes([0x7F, 0x22, 0x31])  # requestOutOfRange

    uds = UdsClient(MockAdapter(handler))
    hits = sweep_dids(uds, _modules()["BCM"], 0xDE00, 0xDE03)
    assert hits == [(0xDE01, bytes([0xAA, 0xBB]))]
