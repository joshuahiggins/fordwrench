from fordwrench.adapter.elm import MockAdapter
from fordwrench.uds.client import UdsClient
from fordwrench.uds.dtc import Dtc, decode_dtc, status_labels


def test_decode_powertrain_code():
    assert decode_dtc(bytes([0x04, 0x20, 0x00])) == "P0420-00"


def test_decode_network_code_with_sub():
    # U: top two bits = 0b11 ; 0xC0,0x73,0x88 -> U0073-88
    assert decode_dtc(bytes([0xC0, 0x73, 0x88]) ) == "U0073-88"


def test_status_labels_confirmed_and_pending():
    labels = status_labels(0b0000_1100)  # bit3 confirmed, bit2 pendingDTC
    assert "confirmed" in labels
    assert "pending" in labels


def test_read_dtcs_parses_records():
    def handler(target, payload):
        assert payload == bytes([0x19, 0x02, 0xFF])
        # 0x59, subfn 0x02, availabilityMask 0xFF, then two 4-byte records
        return bytes([0x59, 0x02, 0xFF,
                      0x04, 0x20, 0x00, 0x08,
                      0xC0, 0x73, 0x88, 0x04])

    uds = UdsClient(MockAdapter(handler))
    dtcs = uds.read_dtcs()
    assert dtcs == [
        Dtc(code="P0420-00", status=0x08),
        Dtc(code="U0073-88", status=0x04),
    ]


def test_read_dtcs_empty_when_no_records():
    def handler(target, payload):
        return bytes([0x59, 0x02, 0xFF])

    uds = UdsClient(MockAdapter(handler))
    assert uds.read_dtcs() == []
