from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Iterable, Set


_loaded_modules: Set[str] = set()


def load_capability_modules(package_names: Iterable[str]) -> list[ModuleType]:
    """Import capability packages so Agent classes can self-register."""
    loaded: list[ModuleType] = []
    for package_name in package_names:
        package = importlib.import_module(package_name)
        loaded.append(package)
        _loaded_modules.add(package.__name__)

        package_path = getattr(package, "__path__", None)
        if package_path is None:
            continue

        for module_info in pkgutil.iter_modules(package_path, package.__name__ + "."):
            if module_info.ispkg:
                continue
            if module_info.name in _loaded_modules:
                continue
            loaded.append(importlib.import_module(module_info.name))
            _loaded_modules.add(module_info.name)
    return loaded
