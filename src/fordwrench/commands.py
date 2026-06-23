from __future__ import annotations

from fordwrench.adapter.elm import AdapterError
from fordwrench.asbuilt.block import AsBuiltBlock
from fordwrench.config import Module
from fordwrench.uds.client import UdsClient
from fordwrench.uds.dtc import Dtc


def probe_modules(adapter, modules: dict[str, Module]) -> list[Module]:
    """Return the modules that answer a tester-present request."""
    responders: list[Module] = []
    for module in modules.values():
        adapter.set_target(module.request_id, module.response_id)
        try:
            adapter.request(bytes([0x3E, 0x00]))
        except AdapterError:
            continue
        responders.append(module)
    return responders


def read_block(uds: UdsClient, module: Module, did: int) -> AsBuiltBlock:
    uds.set_target(module.request_id, module.response_id)
    raw = uds.read_data_by_identifier(did)
    return AsBuiltBlock(module_id=module.request_id, did=did, raw=raw)


def read_module_dtcs(uds: UdsClient, module: Module) -> list[Dtc]:
    uds.set_target(module.request_id, module.response_id)
    return uds.read_dtcs()
