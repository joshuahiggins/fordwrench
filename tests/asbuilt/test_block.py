from fordwrench.asbuilt.block import AsBuiltBlock


def test_label_formats_module_and_did():
    block = AsBuiltBlock(module_id=0x726, did=0xDE00, raw=bytes([0x04, 0x01, 0x00, 0x17]))
    assert block.label == "726-DE00"


def test_data_excludes_trailing_checksum_byte():
    block = AsBuiltBlock(module_id=0x726, did=0xDE00, raw=bytes([0x04, 0x01, 0x00, 0x17]))
    assert block.data == bytes([0x04, 0x01, 0x00])
    assert block.checksum == 0x17


def test_byte_access_by_offset():
    block = AsBuiltBlock(module_id=0x726, did=0xDE00, raw=bytes([0x04, 0x01, 0x00, 0x17]))
    assert block.byte(1) == 0x01


def test_render_is_readable_hex_with_label():
    block = AsBuiltBlock(module_id=0x726, did=0xDE00, raw=bytes([0x04, 0x01, 0x00, 0x17]))
    rendered = block.render()
    assert "726-DE00" in rendered
    assert "04 01 00 17" in rendered
