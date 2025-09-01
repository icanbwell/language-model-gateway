from typing import (
    Any,
    Callable,
    Dict,
    Protocol,
    TypeVar,
    TypeAlias,
    runtime_checkable,
    cast,
)

T = TypeVar("T")
S = TypeVar("S")

# Type definitions
ServiceFactory: TypeAlias = Callable[["SimpleContainer"], T]


@runtime_checkable
class Injectable(Protocol):
    """Marker protocol for injectable services"""


class ContainerError(Exception):
    """Base exception for container errors"""


class ServiceNotFoundError(ContainerError):
    """Raised when a service is not found"""


class SimpleContainer:
    """Generic IoC Container"""

    _singletons: Dict[type[Any], Any] = {}  # Shared across all instances

    def __init__(self) -> None:
        # Remove instance-level _singletons
        self._factories: Dict[type[Any], ServiceFactory[Any]] = {}
        self._singleton_types: set[type[Any]] = set()

    def register(
        self, service_type: type[T], factory: ServiceFactory[T]
    ) -> "SimpleContainer":
        """
        Register a service factory

        Args:
            service_type: The type of service to register
            factory: Factory function that creates the service
        """
        if not callable(factory):
            raise ValueError(f"Factory for {service_type} must be callable")

        self._factories[service_type] = factory
        return self

    def resolve(self, service_type: type[T]) -> T:
        """
        Resolve a service instance

        Args:
            service_type: The type of service to resolve

        Returns:
            An instance of the requested service
        """
        # Check if it's a singleton and already instantiated
        if service_type in SimpleContainer._singletons:
            return cast(T, SimpleContainer._singletons[service_type])

        if service_type not in self._factories:
            raise ServiceNotFoundError(f"No factory registered for {service_type}")

        factory = self._factories[service_type]
        service: T = factory(self)

        # If it's a singleton type, cache the instance
        if service_type in self._singleton_types:
            SimpleContainer._singletons[service_type] = service

        return service

    def singleton(
        self, service_type: type[T], factory: ServiceFactory[T]
    ) -> "SimpleContainer":
        """Register a singleton instance"""
        self._factories[service_type] = factory
        self._singleton_types.add(service_type)
        return self

    def transient(
        self, service_type: type[T], factory: ServiceFactory[T]
    ) -> "SimpleContainer":
        """Register a transient service"""

        def create_new(container: SimpleContainer) -> T:
            return factory(container)

        self.register(service_type, create_new)
        return self
