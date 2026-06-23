import pytest

from fordwrench.adapter.elm import MockAdapter
from fordwrench.uds.client import UdsClient
from fordwrench.uds.errors import NegativeResponse


def test_start_session_sends_correct_request():
    def handler(target, payload):
        assert payload == bytes([0x10, 0x03])
        return bytes([0x50, 0x03, 0x00, 0x32, 0x01, 0xF4])

    uds = UdsClient(MockAdapter(handler))
    uds.start_session(0x03)  # must not raise


def test_read_did_returns_data_after_did_echo():
    def handler(target, payload):
        assert payload == bytes([0x22, 0xDE, 0x00])
        return bytes([0x62, 0xDE, 0x00, 0x04, 0x01, 0x00, 0x17])

    uds = UdsClient(MockAdapter(handler))
    data = uds.read_data_by_identifier(0xDE00)
    assert data == bytes([0x04, 0x01, 0x00, 0x17])


def test_negative_response_raises_with_service_and_nrc():
    def handler(target, payload):
        return bytes([0x7F, 0x22, 0x31])  # requestOutOfRange

    uds = UdsClient(MockAdapter(handler))
    with pytest.raises(NegativeResponse) as exc:
        uds.read_data_by_identifier(0xDE00)
    assert exc.value.service == 0x22
    assert exc.value.nrc == 0x31
    assert "requestOutOfRange" in str(exc.value)


def test_set_target_is_delegated_to_adapter():
    adapter = MockAdapter(lambda t, p: bytes([0x50, 0x03]))
    uds = UdsClient(adapter)
    uds.set_target(0x726, 0x72E)
    assert adapter.target == 0x726
