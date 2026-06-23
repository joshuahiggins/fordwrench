from fordwrench.transport import serial_port


class _FakePort:
    def __init__(self, device, description):
        self.device = device
        self.description = description


def test_lists_ports_macos_style(monkeypatch):
    fake = [_FakePort("/dev/tty.usbserial-1420", "OBDLink EX")]
    monkeypatch.setattr(serial_port, "comports", lambda: fake)
    ports = serial_port.list_serial_ports()
    assert ports == [("/dev/tty.usbserial-1420", "OBDLink EX")]


def test_lists_ports_windows_style(monkeypatch):
    fake = [_FakePort("COM3", "USB Serial Port"), _FakePort("COM5", "OBDLink")]
    monkeypatch.setattr(serial_port, "comports", lambda: fake)
    ports = serial_port.list_serial_ports()
    assert ("COM3", "USB Serial Port") in ports
    assert ("COM5", "OBDLink") in ports
