from fordwrench.transport.base import MockTransport


def test_records_sent_commands_and_returns_mapped_response():
    t = MockTransport({"ATZ": "ELM327 v1.5\r\r>"})
    t.write_command("ATZ")
    resp = t.read_until_prompt()
    assert resp == "ELM327 v1.5\r\r>"
    assert t.sent == ["ATZ"]


def test_unknown_command_returns_no_data_default():
    t = MockTransport()
    t.write_command("ATXYZ")
    assert t.read_until_prompt() == "NO DATA\r>"
