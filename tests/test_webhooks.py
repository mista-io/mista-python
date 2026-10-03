from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from mista import Mista, WebhookVerificationError, verify_webhook

from .conftest import ok

SECRET = "whsec_test"
NOW = 1_790_000_000

EVENT = {
    "id": "evt_1",
    "type": "message.failed",
    "created_at": "2026-10-03T08:00:00+02:00",
    "data": {
        "uid": "m1",
        "to": "250780000001",
        "from": "YourBrand",
        "status": "Undelivered",
        "status_detail": "Undelivered (handset unreachable)",
        "cost": "1",
        "sms_count": 1,
        "campaign_uid": None,
        "sent_at": "2026-10-03T07:59:50+02:00",
        "updated_at": "2026-10-03T08:00:00+02:00",
    },
}
BODY = json.dumps(EVENT)


def sign(body: str, t: int = NOW, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},v1={digest}"


def test_webhook_endpoints(make_client):
    registration = {"url": "https://example.com/hook", "secret": SECRET, "enabled": True, "events": []}
    client, rec = make_client(
        [
            ok(registration),
            ok(registration),
            ok({**registration, "url": None, "secret": None, "enabled": False}),
            ok({"delivered": True, "status_code": 200, "error": None, "event_id": "evt_t"}),
        ]
    )
    assert client.webhooks.get() == registration
    client.webhooks.set(url="https://example.com/hook", rotate_secret=True)
    client.webhooks.delete()
    assert client.webhooks.test()["delivered"] is True

    assert [(c.method, c.path) for c in rec.calls] == [
        ("GET", "/api/v3/webhooks/delivery-reports"),
        ("PUT", "/api/v3/webhooks/delivery-reports"),
        ("DELETE", "/api/v3/webhooks/delivery-reports"),
        ("POST", "/api/v3/webhooks/delivery-reports/test"),
    ]
    assert rec.calls[1].body == {"url": "https://example.com/hook", "rotate_secret": True}


def test_set_omits_rotate_secret_by_default(make_client):
    client, rec = make_client([ok({})])
    client.webhooks.set(url="https://example.com/hook")
    assert rec.calls[0].body == {"url": "https://example.com/hook"}


async def test_async_webhook_endpoints(make_async_client):
    client, rec = make_async_client([ok({"url": None}), ok({"delivered": False, "status_code": 500})])
    await client.webhooks.get()
    assert (await client.webhooks.test())["status_code"] == 500
    assert [c.method for c in rec.calls] == ["GET", "POST"]


def test_verify_returns_the_event():
    assert verify_webhook(BODY, sign(BODY), SECRET, now=NOW) == EVENT
    assert verify_webhook(BODY.encode(), sign(BODY), SECRET, now=NOW)["data"]["status"] == "Undelivered"
    assert Mista("t").webhooks.verify(BODY, sign(BODY), SECRET, tolerance=0)["id"] == "evt_1"


def test_verify_accepts_any_matching_v1():
    header = f"t={NOW},v1={'0' * 64},{sign(BODY).split(',')[1]}"
    assert verify_webhook(BODY, header, SECRET, now=NOW)["id"] == "evt_1"


@pytest.mark.parametrize(
    "payload, header, secret, message",
    [
        (BODY.replace("Undelivered", "Delivered", 1), sign(BODY), SECRET, "does not match"),
        (BODY, sign(BODY), "whsec_other", "does not match"),
        (BODY, None, SECRET, "Missing Mista-Signature"),
        (BODY, "v1=abc", SECRET, "Malformed"),
        (BODY, sign(BODY, NOW - 301), SECRET, "tolerance"),
        (BODY, sign(BODY), "", "Missing webhook secret"),
    ],
)
def test_verify_rejects_bad_requests(payload, header, secret, message):
    with pytest.raises(WebhookVerificationError, match=message):
        verify_webhook(payload, header, secret, now=NOW)


def test_tolerance_zero_skips_age_check():
    assert verify_webhook(BODY, sign(BODY, 1), SECRET, now=NOW, tolerance=0)["id"] == "evt_1"
