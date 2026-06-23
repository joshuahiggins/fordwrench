import pytest

from fordwrench.adapter.elm import AdapterError, ElmAdapter, MockAdapter
from fordwrench.transport.base import MockTransport


def test_initialize_sends_all_init_commands():
    responses = {cmd: "OK\r>" for cmd in ElmAdapter.DEFAULT_INIT}
    responses["ATZ"] = "ELM327 v1.5\r>"
    t = MockTransport(responses)
    ElmAdapter(t).initialize()
    assert t.sent == ElmAdapter.DEFAULT_INIT


def test_initialize_raises_on_error_response():
    t = MockTransport({"ATZ": "?\r>"})
    with pytest.raises(AdapterError):
        ElmAdapter(t).initialize()


def test_set_target_sends_header_and_filter():
    t = MockTransport({"ATSH726": "OK\r>", "ATCRA72E": "OK\r>"})
    ElmAdapter(t).set_target(0x726, 0x72E)
    assert t.sent == ["ATSH726", "ATCRA72E"]


def test_request_parses_single_frame_hex():
    # 0x22 DE00 -> positive response 62 DE00 0401 0017
    t = MockTransport({"22DE00": "62DE0004010017\r>"})
    adapter = ElmAdapter(t)
    resp = adapter.request(bytes([0x22, 0xDE, 0x00]))
    assert resp == bytes([0x62, 0xDE, 0x00, 0x04, 0x01, 0x00, 0x17])


def test_request_assembles_multiline_indexed_response():
    # ELM prints long responses with line-index prefixes 0:, 1:
    t = MockTransport({"22DE00": "0:62DE000401\r1:0017AABB\r>"})
    adapter = ElmAdapter(t)
    resp = adapter.request(bytes([0x22, 0xDE, 0x00]))
    assert resp == bytes([0x62, 0xDE, 0x00, 0x04, 0x01, 0x00, 0x17, 0xAA, 0xBB])


def test_request_raises_on_no_data():
    t = MockTransport({"22DE00": "NO DATA\r>"})
    with pytest.raises(AdapterError):
        ElmAdapter(t).request(bytes([0x22, 0xDE, 0x00]))


def test_mock_adapter_routes_through_handler():
    def handler(target, payload):
        assert target == 0x726
        return bytes([0x62]) + payload[1:]

    a = MockAdapter(handler)
    a.set_target(0x726, 0x72E)
    out = a.request(bytes([0x22, 0xDE, 0x00]))
    assert out == bytes([0x62, 0xDE, 0x00])
    assert a.requests == [(0x726, bytes([0x22, 0xDE, 0x00]))]
