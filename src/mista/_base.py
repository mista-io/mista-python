from __future__ import annotations

import os
import random
from typing import Any, Dict, Mapping, Optional

import httpx

from ._errors import MistaError, error_from_response
from ._operations import Request
from ._version import __version__

DEFAULT_BASE_URL = "https://api.mista.io"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2


class BaseClient:
    def __init__(
        self,
        token: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
    ) -> None:
        token = token or os.environ.get("MISTA_API_TOKEN")
        if not token:
            raise MistaError("Missing API token. Pass token=... or set the MISTA_API_TOKEN environment variable.")
        self._token = token
        self.base_url = (base_url or os.environ.get("MISTA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self, request: Request) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "User-Agent": f"mista-python/{__version__}",
        }
        if request.body is not None:
            headers["Content-Type"] = "application/json"
        return headers

    def _build(self, request: Request) -> Dict[str, Any]:
        return {
            "method": request.method,
            "url": f"{self.base_url}{request.path}",
            "params": {k: v for k, v in request.query.items() if v is not None and v != ""},
            "json": request.body,
            "headers": self._headers(request),
            "timeout": self.timeout,
        }

    def _should_retry_status(self, request: Request, status: int, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        return status == 429 or (status >= 500 and request.method == "GET")

    def _should_retry_connection(self, request: Request, attempt: int) -> bool:
        return request.method == "GET" and attempt < self.max_retries

    @staticmethod
    def _backoff(attempt: int) -> float:
        base = min(8.0, 0.5 * 2.0**attempt)
        return base / 2 + random.random() * (base / 2)

    def _retry_delay(self, attempt: int, headers: Mapping[str, str]) -> float:
        try:
            retry_after = float(headers.get("retry-after", ""))
        except ValueError:
            retry_after = 0
        if retry_after > 0:
            return min(retry_after, 60.0)
        return self._backoff(attempt)

    @staticmethod
    def _parse_body(response: httpx.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def _result(self, response: httpx.Response) -> Any:
        """Return the envelope's ``data``, or raise the matching APIError."""
        body = self._parse_body(response)
        is_error = isinstance(body, dict) and body.get("status") == "error"
        if response.is_success and not is_error:
            if isinstance(body, dict) and body.get("status") == "success" and "data" in body:
                return body["data"]
            return body
        raise error_from_response(response.status_code, body, response.headers)
