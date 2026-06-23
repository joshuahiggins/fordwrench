from fordwrench.config import Module, load_modules


def test_loads_bcm_from_default_registry():
    modules = load_modules()
    assert "BCM" in modules
    bcm = modules["BCM"]
    assert isinstance(bcm, Module)
    assert bcm.request_id == 0x726
    assert bcm.response_id == 0x72E
    assert bcm.security_level == 0x01


def test_loads_from_custom_path(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text(
        "- id: TEST\n"
        "  name: Test Module\n"
        "  request_id: '0x700'\n"
        "  response_id: '0x708'\n"
        "  bus: HS-CAN\n"
        "  security_level: '0x03'\n"
    )
    modules = load_modules(p)
    assert modules["TEST"].request_id == 0x700
    assert modules["TEST"].security_level == 0x03
