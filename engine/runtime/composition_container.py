"""Simple runtime composition binder/resolver."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from engine.api.composition import BindingValue, ServiceBinder, ServiceResolver


class RuntimeCompositionContainer(ServiceBinder):
    """Dependency container with lazy singleton factory resolution."""

    def __init__(self) -> None:
        self._instances: dict[object, BindingValue] = {}
        self._factories: dict[object, Callable[[ServiceResolver], BindingValue]] = {}

    def bind_factory[TBinding: BindingValue](
        self, token: type[TBinding] | object, factory: Callable[[ServiceResolver], TBinding]
    ) -> None:
        self._factories[token] = cast(Callable[[ServiceResolver], BindingValue], factory)
        self._instances.pop(token, None)

    def bind_instance[TBinding: BindingValue](self, token: type[TBinding] | object, instance: TBinding) -> None:
        self._instances[token] = cast(BindingValue, instance)

    def resolve[TBinding: BindingValue](self, token: type[TBinding] | object) -> TBinding:
        if token in self._instances:
            return cast(TBinding, self._instances[token])
        factory = self._factories.get(token)
        if factory is None:
            raise KeyError(f"missing composition binding: {getattr(token, '__qualname__', str(token))}")
        instance = cast(TBinding, factory(self))
        self._instances[token] = cast(BindingValue, instance)
        return instance
