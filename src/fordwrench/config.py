from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    request_id: int
    response_id: int
    bus: str
    security_level: int


def _to_int(value: int | str) -> int:
    return value if isinstance(value, int) else int(value, 0)


def _default_registry_path() -> Path:
    return Path(__file__).parent / "data" / "modules.yaml"


def load_modules(path: Path | str | None = None) -> dict[str, Module]:
    registry_path = Path(path) if path is not None else _default_registry_path()
    raw = yaml.safe_load(registry_path.read_text())
    modules: dict[str, Module] = {}
    for entry in raw:
        module = Module(
            id=entry["id"],
            name=entry["name"],
            request_id=_to_int(entry["request_id"]),
            response_id=_to_int(entry["response_id"]),
            bus=entry["bus"],
            security_level=_to_int(entry["security_level"]),
        )
        modules[module.id] = module
    return modules
