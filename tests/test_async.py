from __future__ import annotations

import pytest

from mista import ServerError

from .conftest import ok, paginated


async def test_send_and_unwrap(make_async_client):
    client, rec = make_async_client([ok({"uid": "m1"})])
    async with client:
        assert await client.sms.send(to="250780000001", sender_id="S", message="hi") == {"uid": "m1"}
    assert rec.calls[0].body == {"recipient": "250780000001", "sender_id": "S", "message": "hi"}


async def test_async_auto_pagination(make_async_client):
    client, rec = make_async_client(
        [ok(paginated([{"uid": "a"}], 1, 2)), ok(paginated([{"uid": "b"}], 2, 2))]
    )
    page = await client.logs.list(status="Delivered")
    assert [m["uid"] async for m in page] == ["a", "b"]
    assert rec.calls[1].query == {"page": "2", "status": "Delivered"}


async def test_async_empty_logs_on_404(make_async_client):
    client, _ = make_async_client([{"status": 404, "json": {"status": "error", "message": "SMS Info not found"}}])
    page = await client.logs.list()
    assert page.items == []


async def test_async_verify_check_false(make_async_client):
    body = {"status": "error", "message": "Verification failed", "data": {"sid": "v1", "status": "expired", "reason": "expired"}}
    client, _ = make_async_client([{"status": 422, "json": body}])
    result = await client.verify.check(sid="v1", code="1")
    assert result["verified"] is False and result["reason"] == "expired"


async def test_async_retry_rules(make_async_client):
    boom = {"status": 500, "json": {"message": "down"}}
    client, rec = make_async_client([boom, ok({})])
    await client.account.balance()
    assert len(rec.calls) == 2

    client, rec = make_async_client([boom])
    with pytest.raises(ServerError):
        await client.contact_groups.create("x")
    assert len(rec.calls) == 1


async def test_async_voice_calls(make_async_client):
    client, rec = make_async_client(
        [ok({"items": [{"uid": "c1"}], "pagination": {"current_page": 1, "per_page": 20, "total": 1, "last_page": 1}})]
    )
    page = await client.voice.calls.list(filter="inbound")
    assert page.items == [{"uid": "c1"}]
    assert rec.calls[0].query == {"filter": "inbound"}
