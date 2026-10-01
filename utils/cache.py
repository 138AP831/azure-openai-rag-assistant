from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ResponseCache(Generic[T]):
    """Small process-local LRU cache for repeated Q&A."""

    def __init__(self, max_items: int = 100) -> None:
        self.max_items = max_items
        self._items: OrderedDict[str, T] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        value = self._items.get(key)

        if value is not None:
            self._items.move_to_end(key)

        return value

    def set(self, key: str, value: T) -> None:
        self._items[key] = value
        self._items.move_to_end(key)

        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
