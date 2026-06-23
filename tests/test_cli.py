from typer.testing import CliRunner

import fordwrench.cli as cli_mod
from fordwrench.adapter.elm import AdapterError, MockAdapter
from fordwrench.uds.client import UdsClient

runner = CliRunner()


def test_scan_lists_ports_when_no_port(monkeypatch):
    monkeypatch.setattr(
        cli_mod, "list_serial_ports", lambda: [("/dev/tty.usbserial-1", "OBDLink EX")]
    )
    result = runner.invoke(cli_mod.app, ["scan"])
    assert result.exit_code == 0
    assert "/dev/tty.usbserial-1" in result.stdout
    assert "OBDLink EX" in result.stdout


def test_scan_probes_modules_when_port_given(monkeypatch):
    def handler(target, payload):
        if target == 0x726:
            return bytes([0x7E, 0x00])
        raise AdapterError("NO DATA")

    monkeypatch.setattr(cli_mod, "build_uds", lambda port: UdsClient(MockAdapter(handler)))
    result = runner.invoke(cli_mod.app, ["scan", "--port", "/dev/fake"])
    assert result.exit_code == 0
    assert "BCM" in result.stdout


def test_read_renders_block(monkeypatch):
    def handler(target, payload):
        return bytes([0x62, 0xDE, 0x00, 0x04, 0x01, 0x00, 0x17])

    monkeypatch.setattr(cli_mod, "build_uds", lambda port: UdsClient(MockAdapter(handler)))
    result = runner.invoke(cli_mod.app, ["read", "BCM", "0xDE00", "--port", "/dev/fake"])
    assert result.exit_code == 0
    assert "726-DE00" in result.stdout
    assert "04 01 00 17" in result.stdout


def test_dtc_renders_codes(monkeypatch):
    def handler(target, payload):
        return bytes([0x59, 0x02, 0xFF, 0x04, 0x20, 0x00, 0x08])

    monkeypatch.setattr(cli_mod, "build_uds", lambda port: UdsClient(MockAdapter(handler)))
    result = runner.invoke(cli_mod.app, ["dtc", "BCM", "--port", "/dev/fake"])
    assert result.exit_code == 0
    assert "P0420-00" in result.stdout
    assert "confirmed" in result.stdout


def test_read_unknown_module_errors(monkeypatch):
    monkeypatch.setattr(cli_mod, "build_uds", lambda port: None)
    result = runner.invoke(cli_mod.app, ["read", "NOPE", "0xDE00", "--port", "/dev/fake"])
    assert result.exit_code != 0
    assert "Unknown module" in result.stdout
