from __future__ import annotations

from fordwrench.adapter.elm import AdapterError
from fordwrench.asbuilt.block import AsBuiltBlock
from fordwrench.config import Module
from fordwrench.uds.client import UdsClient
from fordwrench.uds.dtc import Dtc
from fordwrench.uds.errors import NegativeResponse


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


def read_block(
    uds: UdsClient, module: Module, did: int, extended_session: bool = False
) -> AsBuiltBlock:
    uds.set_target(module.request_id, module.response_id)
    if extended_session:
        uds.start_session(0x03)
    raw = uds.read_data_by_identifier(did)
    return AsBuiltBlock(module_id=module.request_id, did=did, raw=raw)


def read_module_dtcs(uds: UdsClient, module: Module) -> list[Dtc]:
    uds.set_target(module.request_id, module.response_id)
    return uds.read_dtcs()


def sweep_dids(
    uds: UdsClient,
    module: Module,
    start: int,
    end: int,
    extended_session: bool = False,
) -> list[tuple[int, bytes]]:
    """Read every DID in [start, end] and return (did, data) for the ones the
    module supports. Unsupported DIDs (requestOutOfRange) and adapter hiccups
    are skipped. Read-only and non-destructive (UDS service 0x22).

    Some modules only expose their As-Built DIDs after an extended diagnostic
    session; set extended_session=True to send 0x10 0x03 first."""
    uds.set_target(module.request_id, module.response_id)
    if extended_session:
        uds.start_session(0x03)
    hits: list[tuple[int, bytes]] = []
    for did in range(start, end + 1):
        try:
            data = uds.read_data_by_identifier(did)
        except (NegativeResponse, AdapterError):
            continue
        hits.append((did, data))
    return hits
