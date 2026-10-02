from __future__ import annotations

import asyncio
import time
from types import TracebackType
from typing import Any, Optional, Type

import httpx

from ._base import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, BaseClient
from ._errors import APIConnectionError, APITimeoutError
from ._operations import Request
from ._resources import (
    Account,
    AsyncAccount,
    AsyncCampaigns,
    AsyncContactGroups,
    AsyncContacts,
    AsyncLogs,
    AsyncSms,
    AsyncVerify,
    AsyncVoice,
    Campaigns,
    ContactGroups,
    Contacts,
    Logs,
    Sms,
    Verify,
    Voice,
)


class Mista(BaseClient):
    """Synchronous Mista client.

    >>> mista = Mista(token="...")  # or set MISTA_API_TOKEN
    >>> mista.sms.send(to="250780000001", sender_id="YourBrand", message="Hello")
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(token, base_url, timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client()
        self.sms = Sms(self)
        self.campaigns = Campaigns(self)
        self.logs = Logs(self)
        self.account = Account(self)
        self.contact_groups = ContactGroups(self)
        self.contacts = Contacts(self)
        self.verify = Verify(self)
        self.voice = Voice(self)

    def request(self, request: Request) -> Any:
        """Send a request and return the ``data`` field of the response envelope."""
        attempt = 0
        while True:
            try:
                response = self._http.request(**self._build(request))
            except httpx.TimeoutException as exc:
                error: APIConnectionError = APITimeoutError(f"Request timed out after {self.timeout}s")
                cause: Exception = exc
            except httpx.TransportError as exc:
                error = APIConnectionError(f"Could not reach {self.base_url}: {exc}")
                cause = exc
            else:
                if self._should_retry_status(request, response.status_code, attempt):
                    time.sleep(self._retry_delay(attempt, response.headers))
                    attempt += 1
                    continue
                return self._result(response)
            if self._should_retry_connection(request, attempt):
                time.sleep(self._backoff(attempt))
                attempt += 1
                continue
            raise error from cause

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> "Mista":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()


class AsyncMista(BaseClient):
    """Asynchronous Mista client. Use ``async with AsyncMista() as mista:``."""

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(token, base_url, timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient()
        self.sms = AsyncSms(self)
        self.campaigns = AsyncCampaigns(self)
        self.logs = AsyncLogs(self)
        self.account = AsyncAccount(self)
        self.contact_groups = AsyncContactGroups(self)
        self.contacts = AsyncContacts(self)
        self.verify = AsyncVerify(self)
        self.voice = AsyncVoice(self)

    async def request(self, request: Request) -> Any:
        """Send a request and return the ``data`` field of the response envelope."""
        attempt = 0
        while True:
            try:
                response = await self._http.request(**self._build(request))
            except httpx.TimeoutException as exc:
                error: APIConnectionError = APITimeoutError(f"Request timed out after {self.timeout}s")
                cause: Exception = exc
            except httpx.TransportError as exc:
                error = APIConnectionError(f"Could not reach {self.base_url}: {exc}")
                cause = exc
            else:
                if self._should_retry_status(request, response.status_code, attempt):
                    await asyncio.sleep(self._retry_delay(attempt, response.headers))
                    attempt += 1
                    continue
                return self._result(response)
            if self._should_retry_connection(request, attempt):
                await asyncio.sleep(self._backoff(attempt))
                attempt += 1
                continue
            raise error from cause

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncMista":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()
