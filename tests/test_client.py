from __future__ import annotations

import httpx
import pytest

from mista import (
    __version__,
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    FieldError,
    Mista,
    MistaError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    ValidationError,
)

from .conftest import ok


def test_headers_and_base_url(make_client):
    client, rec = make_client([ok({"remaining_unit": "10"})])
    client.account.balance()
    call = rec.calls[0]
    assert str(call.url) == "https://api.mista.io/api/v3/balance"
    assert call.headers["authorization"] == "Bearer test-token"
    assert call.headers["accept"] == "application/json"
    assert call.headers["user-agent"] == f"mista-python/{__version__}"
    assert "content-type" not in call.headers


def test_unwraps_envelope(make_client):
    client, _ = make_client([ok({"remaining_unit": "1,250", "expired_on": "x"})])
    assert client.account.balance() == {"remaining_unit": "1,250", "expired_on": "x"}


def test_token_from_env(monkeypatch):
    monkeypatch.delenv("MISTA_API_TOKEN", raising=False)
    with pytest.raises(MistaError):
        Mista()
    monkeypatch.setenv("MISTA_API_TOKEN", "env-token")
    with Mista() as client:
        assert client._token == "env-token"


def test_custom_base_url():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"status": "success", "data": {}})

    client = Mista("t", base_url="https://example.test/", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    client.account.me()
    assert seen == ["https://example.test/api/v3/account/me"]


@pytest.mark.parametrize(
    "status,cls",
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (422, ValidationError),
        (418, APIError),
    ],
)
def test_status_mapping(make_client, status, cls):
    client, _ = make_client([{"status": status, "json": {"status": "error", "message": "nope"}}])
    with pytest.raises(cls) as info:
        client.account.me()
    assert info.value.status == status
    assert str(info.value) == "nope"


def test_200_with_error_status_raises(make_client):
    client, _ = make_client([{"json": {"status": "error", "message": "You have already subscribed to Developers"}}])
    with pytest.raises(APIError, match="already subscribed"):
        client.contacts.create("g1", phone="250780000001")


def test_fastapi_field_errors(make_client):
    detail = [{"type": "missing", "loc": ["body", "sender_id"], "msg": "Field required", "input": None}]
    client, _ = make_client([{"status": 422, "json": {"detail": detail}}])
    with pytest.raises(ValidationError) as info:
        client.sms.send(to="250780000001", sender_id="", message="hi")
    assert str(info.value) == "sender_id: Field required"
    assert info.value.errors == [FieldError("sender_id", "Field required", "missing")]


def test_laravel_field_errors(make_client):
    body = {"message": "The name field is required.", "errors": {"name": ["The name field is required."]}}
    client, _ = make_client([{"status": 422, "json": body}])
    with pytest.raises(ValidationError) as info:
        client.contact_groups.create("")
    assert info.value.errors == [FieldError("name", "The name field is required.")]


def test_retries_429_for_post(make_client):
    limited = {"status": 429, "json": {"message": "Too Many Attempts."}, "headers": {"Retry-After": "1"}}
    client, rec = make_client([limited, ok({"uid": "m1"})])
    assert client.sms.send(to="250780000001", sender_id="S", message="hi") == {"uid": "m1"}
    assert len(rec.calls) == 2


def test_rate_limit_after_retries(make_client):
    limited = {"status": 429, "json": {"message": "Too Many Attempts."}, "headers": {"Retry-After": "7"}}
    client, rec = make_client([limited, limited, limited])
    with pytest.raises(RateLimitError) as info:
        client.account.me()
    assert info.value.retry_after == 7
    assert len(rec.calls) == 3


def test_5xx_retried_for_get_only(make_client):
    boom = {"status": 503, "json": {"status": "error", "message": "down"}}
    client, rec = make_client([boom, ok({})])
    client.account.me()
    assert len(rec.calls) == 2

    client, rec = make_client([boom, ok({})])
    with pytest.raises(ServerError):
        client.sms.send(to="250780000001", sender_id="S", message="hi")
    assert len(rec.calls) == 1


def test_connection_errors_retried_for_get_only(make_client):
    client, rec = make_client([httpx.ConnectError("refused"), ok({})])
    client.account.me()
    assert len(rec.calls) == 2

    client, rec = make_client([httpx.ConnectError("refused")])
    with pytest.raises(APIConnectionError):
        client.contact_groups.create("x")
    assert len(rec.calls) == 1


def test_max_retries_zero(make_client):
    boom = {"status": 503, "json": {"message": "down"}}
    client, rec = make_client([boom, ok({})], max_retries=0)
    with pytest.raises(ServerError):
        client.account.me()
    assert len(rec.calls) == 1
