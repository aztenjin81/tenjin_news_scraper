from tenjin.sources.base import SourceAdapter

_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(name: str):
    def decorator(cls: type[SourceAdapter]) -> type[SourceAdapter]:
        _REGISTRY[name] = cls
        return cls

    return decorator


def get(name: str) -> type[SourceAdapter]:
    return _REGISTRY[name]


def all_adapters() -> dict[str, type[SourceAdapter]]:
    return dict(_REGISTRY)
