from __future__ import annotations

from app.agents.base import CapabilityAgent
from app.registry.base import CapabilityRegistrar


_active_registrar: CapabilityRegistrar | None = None


def set_active_registrar(registrar: CapabilityRegistrar) -> None:
    global _active_registrar
    _active_registrar = registrar


def get_active_registrar() -> CapabilityRegistrar:
    if _active_registrar is None:
        raise RuntimeError("Capability registrar has not been initialized")
    return _active_registrar


def register_capability(agent_cls: type[CapabilityAgent]) -> type[CapabilityAgent]:
    registrar = get_active_registrar()
    registrar.register_local(agent_cls())
    return agent_cls
