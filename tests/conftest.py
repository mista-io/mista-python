from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
import pytest

from mista import AsyncMista, Mista


@dataclass
class Call:
    method: str
    url: httpx.URL
    headers: httpx.Headers
    body: Any

    @property
    def path(self) -> str:
        return self.url.path

    @property
    def query(self) -> Dict[str, str]:
        return dict(self.url.params)


Reply = Union[Dict[str, Any], Exception]


def ok(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    return {"json": {"status": "success", "message": message, "data": data}}


def paginated(rows: List[Any], current_page: int = 1, last_page: int = 1) -> Dict[str, Any]:
    return {"current_page": current_page, "data": rows, "last_page": last_page, "per_page": 25, "total": len(rows)}


class Recorder:
    """Replays ``replies`` in order and records every request."""

    def __init__(self, replies: List[Reply]) -> None:
        self.replies = list(replies)
        self.calls: List[Call] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append(Call(request.method, request.url, request.headers, body))
        reply = self.replies.pop(0) if self.replies else ok(None)
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(reply.get("status", 200), json=reply.get("json"), headers=reply.get("headers"))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr("mista._client.time.sleep", lambda _: None)
    monkeypatch.setattr("mista._client.asyncio.sleep", instant)


@pytest.fixture
def make_client() -> Callable[..., "tuple[Mista, Recorder]"]:
    def factory(replies: List[Reply], max_retries: int = 2) -> "tuple[Mista, Recorder]":
        recorder = Recorder(replies)
        http = httpx.Client(transport=httpx.MockTransport(recorder))
        return Mista("test-token", http_client=http, max_retries=max_retries), recorder

    return factory


@pytest.fixture
def make_async_client() -> Callable[..., "tuple[AsyncMista, Recorder]"]:
    def factory(replies: List[Reply], max_retries: int = 2) -> "tuple[AsyncMista, Recorder]":
        recorder = Recorder(replies)
        http = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
        return AsyncMista("test-token", http_client=http, max_retries=max_retries), recorder

    return factory
