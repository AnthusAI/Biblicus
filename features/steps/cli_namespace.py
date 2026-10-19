"""
Package-wide view of the Biblicus command-line interface command group modules.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Any, List

import biblicus.cli as cli_package


class CommandLineInterfaceNamespace:
    """
    Attribute view across every module of the ``biblicus.cli`` package.

    Reading an attribute resolves it from the module that defines it. Writing an attribute
    rebinds it in every module that holds a reference, so a test double replaces a dependency
    for every command group that uses it.
    """

    def _modules(self) -> List[ModuleType]:
        """
        List the command group modules of the command-line interface package.

        :return: Imported package modules, with the package itself first.
        :rtype: list[ModuleType]
        """
        modules = [cli_package]
        for module_info in pkgutil.iter_modules(cli_package.__path__):
            modules.append(importlib.import_module(f"{cli_package.__name__}.{module_info.name}"))
        return modules

    def __getattr__(self, name: str) -> Any:
        """
        Resolve an attribute from the module that defines it.

        :param name: Attribute name.
        :type name: str
        :return: Attribute value.
        :rtype: Any
        :raises AttributeError: If no module of the package has the attribute.
        """
        holders = [module for module in self._modules() if hasattr(module, name)]
        if not holders:
            raise AttributeError(name)
        for module in holders:
            if getattr(getattr(module, name), "__module__", None) == module.__name__:
                return getattr(module, name)
        return getattr(holders[0], name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Rebind an attribute in every module of the package that holds it.

        :param name: Attribute name.
        :type name: str
        :param value: Replacement value.
        :type value: Any
        :return: None.
        :rtype: None
        :raises AttributeError: If no module of the package has the attribute.
        """
        holders = [module for module in self._modules() if hasattr(module, name)]
        if not holders:
            raise AttributeError(name)
        for module in holders:
            setattr(module, name, value)


cli_namespace = CommandLineInterfaceNamespace()
