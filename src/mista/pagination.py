from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PageMeta:
    current_page: int
    last_page: int
    per_page: int
    total: int


def _int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def parse_page(raw: Any) -> "tuple[List[Any], PageMeta]":
    """Read either the Laravel paginator ``{current_page, data, ...}`` or the
    Voice shape ``{items, pagination: {...}}``."""
    raw = raw if isinstance(raw, dict) else {}
    if "items" in raw:
        items = raw.get("items") or []
        meta = raw.get("pagination") or {}
    else:
        items = raw.get("data") or []
        meta = raw
    items = items if isinstance(items, list) else []
    return items, PageMeta(
        current_page=_int(meta.get("current_page"), 1),
        last_page=_int(meta.get("last_page"), 1),
        per_page=_int(meta.get("per_page"), len(items)),
        total=_int(meta.get("total"), len(items)),
    )


EMPTY_META = PageMeta(current_page=1, last_page=1, per_page=0, total=0)


class Page(Generic[T]):
    """One page of results. Iterating the page walks every item across all
    remaining pages; ``items`` holds just this page."""

    def __init__(self, items: List[T], meta: PageMeta, fetch_page: Callable[[int], "Page[T]"]) -> None:
        self.items = items
        self.meta = meta
        self._fetch_page = fetch_page

    def has_next_page(self) -> bool:
        return self.meta.current_page < self.meta.last_page

    def next_page(self) -> Optional["Page[T]"]:
        return self._fetch_page(self.meta.current_page + 1) if self.has_next_page() else None

    def __iter__(self) -> Iterator[T]:
        page: Optional[Page[T]] = self
        while page is not None:
            yield from page.items
            page = page.next_page()

    def __repr__(self) -> str:
        return f"Page(items={len(self.items)}, meta={self.meta})"


class AsyncPage(Generic[T]):
    """Async counterpart of :class:`Page`; use ``async for`` to walk every item."""

    def __init__(
        self, items: List[T], meta: PageMeta, fetch_page: Callable[[int], Awaitable["AsyncPage[T]"]]
    ) -> None:
        self.items = items
        self.meta = meta
        self._fetch_page = fetch_page

    def has_next_page(self) -> bool:
        return self.meta.current_page < self.meta.last_page

    async def next_page(self) -> Optional["AsyncPage[T]"]:
        return await self._fetch_page(self.meta.current_page + 1) if self.has_next_page() else None

    async def __aiter__(self) -> AsyncIterator[T]:
        page: Optional[AsyncPage[T]] = self
        while page is not None:
            for item in page.items:
                yield item
            page = await page.next_page()

    def __repr__(self) -> str:
        return f"AsyncPage(items={len(self.items)}, meta={self.meta})"
