from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class FieldError:
    """One field problem reported by the API (FastAPI ``detail[]`` or Laravel ``errors``)."""

    field: Optional[str]
    message: str
    type: Optional[str] = None


class MistaError(Exception):
    """Base class for every error raised by this package."""


class APIError(MistaError):
    """The API answered with an error status, or a 200 whose body says ``"status": "error"``."""

    def __init__(self, message: str, status: int, body: Any, headers: Mapping[str, str]) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body
        self.headers = headers
        self.errors = parse_field_errors(body)


class BadRequestError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class PermissionDeniedError(APIError):
    pass


class NotFoundError(APIError):
    pass


class ValidationError(APIError):
    pass


class RateLimitError(APIError):
    @property
    def retry_after(self) -> Optional[float]:
        """Seconds to wait before retrying, from the ``Retry-After`` header."""
        return _positive_float(self.headers.get("retry-after"))


class ServerError(APIError):
    pass


class APIConnectionError(MistaError):
    pass


class APITimeoutError(APIConnectionError):
    pass


def _positive_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def parse_field_errors(body: Any) -> list[FieldError]:
    if not isinstance(body, dict):
        return []
    detail = body.get("detail")
    if isinstance(detail, list):
        result = []
        for item in detail:
            if not isinstance(item, dict):
                continue
            loc = item.get("loc")
            if not isinstance(loc, list):
                loc = []
            field = str(loc[-1]) if len(loc) > 1 else None
            kind = item.get("type")
            result.append(FieldError(field, str(item.get("msg", "")), None if kind is None else str(kind)))
        return result
    errors = body.get("errors")
    if isinstance(errors, dict):
        return [
            FieldError(field, str(message))
            for field, messages in errors.items()
            for message in (messages if isinstance(messages, list) else [messages])
        ]
    return []


def error_message(body: Any, status: int) -> str:
    if isinstance(body, dict):
        for key in ("message", "detail"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value
        errors = parse_field_errors(body)
        if errors:
            first = errors[0]
            return f"{first.field}: {first.message}" if first.field else first.message
    if isinstance(body, str) and body.strip():
        return body[:300]
    return f"Request failed with status {status}"


def error_from_response(status: int, body: Any, headers: Mapping[str, str]) -> APIError:
    message = error_message(body, status)
    cls: type[APIError] = {
        400: BadRequestError,
        401: AuthenticationError,
        403: PermissionDeniedError,
        404: NotFoundError,
        422: ValidationError,
        429: RateLimitError,
    }.get(status, ServerError if status >= 500 else APIError)
    return cls(message, status, body, headers)
