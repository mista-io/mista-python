from __future__ import annotations

from datetime import datetime

import pytest

from mista import APIError, MistaError

from .conftest import ok, paginated


def test_sms_send(make_client):
    client, rec = make_client([ok({"uid": "m1", "status": "Queued"})])
    client.sms.send(to="250780000001", sender_id="YourBrand", message="Hello", type="plain")
    call = rec.calls[0]
    assert (call.method, call.path) == ("POST", "/api/v3/sms")
    assert call.body == {"recipient": "250780000001", "sender_id": "YourBrand", "message": "Hello", "type": "plain"}
    assert call.headers["content-type"] == "application/json"


def test_sms_send_rejects_many_recipients(make_client):
    client, rec = make_client([])
    with pytest.raises(MistaError):
        client.sms.send(to="250780000001,250780000002", sender_id="S", message="x")
    assert rec.calls == []


def test_bulk_broadcast_with_schedule(make_client):
    client, rec = make_client([ok({"uid": "c1"})])
    client.campaigns.bulk(
        sender_id="LOYALTY",
        recipients=["250780000001", "250780000002"],
        message="Double points!",
        schedule_time=datetime(2026, 12, 24, 9, 5),
    )
    assert rec.calls[0].path == "/api/v3/campaigns/bulk"
    assert rec.calls[0].body == {
        "sender_id": "LOYALTY",
        "recipients": ["250780000001", "250780000002"],
        "message": "Double points!",
        "schedule_time": "2026-12-24 09:05",
    }


def test_bulk_personalized_drops_message(make_client):
    client, rec = make_client([ok({"uid": "c1"})])
    client.campaigns.bulk(
        sender_id="LOYALTY", recipients=[{"to": "250780000001", "message": "Hi Alice"}], message="ignored"
    )
    assert rec.calls[0].body == {"sender_id": "LOYALTY", "recipients": [{"to": "250780000001", "message": "Hi Alice"}]}


def test_bulk_validation(make_client):
    client, _ = make_client([])
    with pytest.raises(MistaError, match="not both"):
        client.campaigns.bulk(sender_id="S", recipients=["1", {"to": "2", "message": "x"}], message="m")
    with pytest.raises(MistaError, match="message is required"):
        client.campaigns.bulk(sender_id="S", recipients=["250780000001"])
    with pytest.raises(MistaError, match="empty"):
        client.campaigns.bulk(sender_id="S", recipients=[])
    with pytest.raises(MistaError, match="10000"):
        client.campaigns.bulk(sender_id="S", recipients=["250780000001"] * 10_001, message="m")


def test_send_to_groups(make_client):
    client, rec = make_client([ok({"uid": "c2"})])
    client.campaigns.send_to_groups(group_uids=["g1", "g2"], sender_id="S", message="Hi")
    assert rec.calls[0].path == "/api/v3/sms/campaign"
    assert rec.calls[0].body == {"contact_list_id": "g1,g2", "sender_id": "S", "message": "Hi"}


def test_campaign_get(make_client):
    client, rec = make_client([ok({"id": "c1"})])
    client.campaigns.get("c1")
    assert (rec.calls[0].method, rec.calls[0].path) == ("GET", "/api/v3/campaign/c1/view")


def test_logs_list_filters_and_auto_pagination(make_client):
    client, rec = make_client(
        [ok(paginated([{"uid": "a"}, {"uid": "b"}], 1, 2)), ok(paginated([{"uid": "c"}], 2, 2))]
    )
    page = client.logs.list(start_date="2026-10-01", status="Delivered", sender_id="BRAND", per_page=2)
    assert [m["uid"] for m in page.items] == ["a", "b"]
    assert page.has_next_page()
    assert rec.calls[0].path == "/api/v3/log/view"
    assert rec.calls[0].query == {"start_date": "2026-10-01", "status": "Delivered", "from": "BRAND", "per_page": "2"}

    assert [m["uid"] for m in page] == ["a", "b", "c"]
    assert rec.calls[1].query["page"] == "2"
    assert rec.calls[1].query["from"] == "BRAND"


def test_logs_list_empty_on_404(make_client):
    client, _ = make_client([{"status": 404, "json": {"status": "error", "message": "SMS Info not found"}}])
    page = client.logs.list(sender_id="Nobody")
    assert page.items == []
    assert not page.has_next_page()


def test_logs_get(make_client):
    client, rec = make_client([ok({"uid": "m1"})])
    client.logs.get("m1")
    assert rec.calls[0].path == "/api/v3/log/m1"


def test_contact_groups(make_client):
    client, rec = make_client(
        [
            ok(paginated([{"uid": "g1", "name": "Devs"}])),
            ok({"uid": "g1", "name": "Devs"}),
            ok({"uid": "g1", "name": "Devs"}),
            ok({"uid": "g1", "name": "Devs KGL"}),
            ok(None, "Contact group was successfully deleted"),
        ]
    )
    assert client.contact_groups.list().items == [{"uid": "g1", "name": "Devs"}]
    client.contact_groups.create("Devs")
    client.contact_groups.get("g1")
    client.contact_groups.update("g1", "Devs KGL")
    assert client.contact_groups.delete("g1") is None
    assert [f"{c.method} {c.path}" for c in rec.calls] == [
        "GET /api/v3/contacts",
        "POST /api/v3/contacts",
        "POST /api/v3/contacts/g1/show",
        "PATCH /api/v3/contacts/g1",
        "DELETE /api/v3/contacts/g1",
    ]
    assert rec.calls[1].body == {"name": "Devs"}
    assert rec.calls[4].body is None


def test_contacts_use_field_tags(make_client):
    client, rec = make_client([ok({"uid": "c1"}), ok({"uid": "c1"})])
    client.contacts.create("g1", phone="250780000001", first_name="Alice", last_name="Uwase", fields={"CITY": "Kigali"})
    client.contacts.update("g1", "c1", phone="250780000001", first_name="Alicia")
    assert rec.calls[0].path == "/api/v3/contacts/g1/store"
    assert rec.calls[0].body == {"CITY": "Kigali", "PHONE": "250780000001", "FIRST_NAME": "Alice", "LAST_NAME": "Uwase"}
    assert (rec.calls[1].method, rec.calls[1].path) == ("PATCH", "/api/v3/contacts/g1/update/c1")
    assert rec.calls[1].body == {"PHONE": "250780000001", "FIRST_NAME": "Alicia"}


def test_contacts_list_get_delete(make_client):
    client, rec = make_client([ok(paginated([{"uid": "c1"}])), ok({"uid": "c1"}), ok(None)])
    client.contacts.list("g1", page=3)
    client.contacts.get("g1", "c1")
    client.contacts.delete("g1", "c1")
    assert [f"{c.method} {c.url.raw_path.decode()}" for c in rec.calls] == [
        "GET /api/v3/contacts/g1/all?page=3",
        "POST /api/v3/contacts/g1/search/c1",
        "DELETE /api/v3/contacts/g1/delete/c1",
    ]


def test_path_segments_are_escaped(make_client):
    client, rec = make_client([ok({})])
    client.logs.get("a/b")
    assert rec.calls[0].url.raw_path == b"/api/v3/log/a%2Fb"


def test_verify_start(make_client):
    client, rec = make_client([ok({"sid": "v1"})])
    client.verify.start(to="+250780000001", channel="sms", sender_id="MISTA")
    assert rec.calls[0].path == "/api/v3/verify"
    assert rec.calls[0].body == {"to": "+250780000001", "channel": "sms", "sender_id": "MISTA"}


def test_verify_check_success(make_client):
    client, rec = make_client([ok({"sid": "v1", "status": "approved", "verified_at": "t"})])
    assert client.verify.check(sid="v1", code="123456") == {
        "verified": True,
        "sid": "v1",
        "status": "approved",
        "verified_at": "t",
    }
    assert rec.calls[0].path == "/api/v3/verify/check"


def test_verify_check_wrong_code_returns_false(make_client):
    body = {"status": "error", "message": "Verification failed", "data": {"sid": "v1", "status": "pending", "reason": "invalid_code"}}
    client, _ = make_client([{"status": 422, "json": body}])
    assert client.verify.check(sid="v1", code="000000") == {
        "verified": False,
        "sid": "v1",
        "status": "pending",
        "reason": "invalid_code",
    }


def test_verify_check_other_errors_raise(make_client):
    client, _ = make_client([{"status": 422, "json": {"status": "error", "message": "Verification not found."}}])
    with pytest.raises(APIError, match="Verification not found."):
        client.verify.check(sid="nope", code="1")


def test_verify_get(make_client):
    client, rec = make_client([ok({"sid": "v1"})])
    client.verify.get("v1")
    assert rec.calls[0].path == "/api/v3/verify/v1"


def test_voice(make_client):
    client, rec = make_client(
        [
            ok({"token": "jwt"}),
            ok([{"uid": "n1", "number": "+250780000001"}]),
            ok({"items": [{"uid": "call1"}], "pagination": {"current_page": 1, "per_page": 20, "total": 1, "last_page": 1}}),
            ok({"uid": "call1"}),
        ]
    )
    client.voice.access_token(platform="ios")
    assert len(client.voice.numbers()) == 1
    page = client.voice.calls.list(filter="missed", per_page=20)
    assert page.items == [{"uid": "call1"}]
    assert (page.meta.current_page, page.meta.last_page, page.meta.per_page, page.meta.total) == (1, 1, 20, 1)
    client.voice.calls.get("call1")
    assert [f"{c.method} {c.url.raw_path.decode()}" for c in rec.calls] == [
        "GET /api/v3/voice/access-token?platform=ios",
        "GET /api/v3/voice/numbers",
        "GET /api/v3/voice/calls?filter=missed&per_page=20",
        "GET /api/v3/voice/calls/call1",
    ]
