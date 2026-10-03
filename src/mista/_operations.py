"""Pure request builders shared by the sync and async clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence, Union
from urllib.parse import quote

from ._errors import MistaError
MAX_BULK_RECIPIENTS = 10_000

ScheduleTime = Union[str, datetime]
Recipients = Union[Sequence[str], Sequence[Mapping[str, str]]]
"""Phone strings (broadcast) or ``{"to": ..., "message": ...}`` dicts (personalized)."""


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: Dict[str, Any] = field(default_factory=dict)
    body: Any = None


def _seg(value: str) -> str:
    return quote(str(value), safe="")


def _compact(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def format_schedule_time(value: Optional[ScheduleTime]) -> Optional[str]:
    """``Y-m-d H:i`` in the account timezone. A datetime's own wall-clock time is used as-is."""
    if value is None or isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ SMS


def sms_send(
    to: str,
    sender_id: str,
    message: str,
    type: Optional[str] = None,
    media_url: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    dlt_template_id: Optional[str] = None,
) -> Request:
    if not isinstance(to, str) or "," in to:
        raise MistaError("sms.send() takes one recipient. Use campaigns.bulk() for several numbers.")
    return Request(
        "POST",
        "/api/v3/sms",
        body=_compact(
            {
                "recipient": to,
                "sender_id": sender_id,
                "message": message,
                "type": type,
                "media_url": media_url,
                "language": language,
                "gender": gender,
                "dlt_template_id": dlt_template_id,
            }
        ),
    )


# ------------------------------------------------------------ Campaigns


def campaigns_bulk(
    sender_id: str,
    recipients: Recipients,
    message: Optional[str] = None,
    type: Optional[str] = None,
    name: Optional[str] = None,
    schedule_time: Optional[ScheduleTime] = None,
    dlt_template_id: Optional[str] = None,
) -> Request:
    items = list(recipients)
    if not items:
        raise MistaError("recipients must not be empty.")
    if len(items) > MAX_BULK_RECIPIENTS:
        raise MistaError(f"At most {MAX_BULK_RECIPIENTS} recipients per request.")
    strings = sum(isinstance(item, str) for item in items)
    if strings and strings != len(items):
        raise MistaError("Use either phone strings (broadcast) or {to, message} dicts, not both.")
    if strings and not message:
        raise MistaError("message is required when recipients are phone strings.")
    return Request(
        "POST",
        "/api/v3/campaigns/bulk",
        body=_compact(
            {
                "sender_id": sender_id,
                "recipients": items,
                "message": message if strings else None,
                "type": type,
                "name": name,
                "schedule_time": format_schedule_time(schedule_time),
                "dlt_template_id": dlt_template_id,
            }
        ),
    )


def campaigns_send_to_groups(
    group_uids: Union[str, Sequence[str]],
    sender_id: str,
    message: str,
    type: Optional[str] = None,
    schedule_time: Optional[ScheduleTime] = None,
    dlt_template_id: Optional[str] = None,
) -> Request:
    groups = [group_uids] if isinstance(group_uids, str) else list(group_uids)
    if not groups:
        raise MistaError("group_uids must not be empty.")
    return Request(
        "POST",
        "/api/v3/sms/campaign",
        body=_compact(
            {
                "contact_list_id": ",".join(groups),
                "sender_id": sender_id,
                "message": message,
                "type": type,
                "schedule_time": format_schedule_time(schedule_time),
                "dlt_template_id": dlt_template_id,
            }
        ),
    )


def campaigns_get(uid: str) -> Request:
    return Request("GET", f"/api/v3/campaign/{_seg(uid)}/view")


# ----------------------------------------------------------------- Logs


def logs_list(
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sender_id: Optional[str] = None,
    status: Optional[str] = None,
    sms_type: Optional[str] = None,
) -> Request:
    return Request(
        "GET",
        "/api/v3/log/view",
        query={
            "page": page,
            "per_page": per_page,
            "start_date": start_date,
            "end_date": end_date,
            "from": sender_id,
            "status": status,
            "sms_type": sms_type,
        },
    )


def logs_get(uid: str) -> Request:
    return Request("GET", f"/api/v3/log/{_seg(uid)}")


# -------------------------------------------------------------- Account


def account_balance() -> Request:
    return Request("GET", "/api/v3/balance")


def account_me() -> Request:
    return Request("GET", "/api/v3/account/me")


# ------------------------------------------------------- Contact groups


def groups_list(page: Optional[int] = None) -> Request:
    return Request("GET", "/api/v3/contacts", query={"page": page})


def groups_create(name: str) -> Request:
    return Request("POST", "/api/v3/contacts", body={"name": name})


def groups_get(group_uid: str) -> Request:
    return Request("POST", f"/api/v3/contacts/{_seg(group_uid)}/show")


def groups_update(group_uid: str, name: str) -> Request:
    return Request("PATCH", f"/api/v3/contacts/{_seg(group_uid)}", body={"name": name})


def groups_delete(group_uid: str) -> Request:
    return Request("DELETE", f"/api/v3/contacts/{_seg(group_uid)}")


# ------------------------------------------------------------- Contacts


def _contact_body(
    phone: str,
    first_name: Optional[str],
    last_name: Optional[str],
    fields: Optional[Mapping[str, str]],
) -> Dict[str, Any]:
    """Contact fields are sent by their group field tag (PHONE, FIRST_NAME, LAST_NAME, custom tags)."""
    return _compact({**(fields or {}), "PHONE": phone, "FIRST_NAME": first_name, "LAST_NAME": last_name})


def contacts_create(
    group_uid: str,
    phone: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    fields: Optional[Mapping[str, str]] = None,
) -> Request:
    return Request(
        "POST",
        f"/api/v3/contacts/{_seg(group_uid)}/store",
        body=_contact_body(phone, first_name, last_name, fields),
    )


def contacts_list(group_uid: str, page: Optional[int] = None) -> Request:
    return Request("GET", f"/api/v3/contacts/{_seg(group_uid)}/all", query={"page": page})


def contacts_get(group_uid: str, uid: str) -> Request:
    return Request("POST", f"/api/v3/contacts/{_seg(group_uid)}/search/{_seg(uid)}")


def contacts_update(
    group_uid: str,
    uid: str,
    phone: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    fields: Optional[Mapping[str, str]] = None,
) -> Request:
    return Request(
        "PATCH",
        f"/api/v3/contacts/{_seg(group_uid)}/update/{_seg(uid)}",
        body=_contact_body(phone, first_name, last_name, fields),
    )


def contacts_delete(group_uid: str, uid: str) -> Request:
    return Request("DELETE", f"/api/v3/contacts/{_seg(group_uid)}/delete/{_seg(uid)}")


# --------------------------------------------------------------- Verify


def verify_start(to: str, channel: Optional[str] = None, sender_id: Optional[str] = None) -> Request:
    return Request("POST", "/api/v3/verify", body=_compact({"to": to, "channel": channel, "sender_id": sender_id}))


def verify_check(sid: str, code: str) -> Request:
    return Request("POST", "/api/v3/verify/check", body={"sid": sid, "code": code})


def verify_get(sid: str) -> Request:
    return Request("GET", f"/api/v3/verify/{_seg(sid)}")


def failed_check(error: Exception) -> Optional[Dict[str, Any]]:
    """The ``data`` of a 422 "Verification failed" answer, or None for any other error."""
    from ._errors import ValidationError

    if isinstance(error, ValidationError) and isinstance(error.body, dict):
        data = error.body.get("data")
        if isinstance(data, dict) and "reason" in data:
            return data
    return None


# ------------------------------------------------------------- Webhooks

WEBHOOKS_PATH = "/api/v3/webhooks/delivery-reports"


def webhooks_get() -> Request:
    return Request("GET", WEBHOOKS_PATH)


def webhooks_set(url: str, rotate_secret: Optional[bool] = None) -> Request:
    return Request("PUT", WEBHOOKS_PATH, body=_compact({"url": url, "rotate_secret": rotate_secret or None}))


def webhooks_delete() -> Request:
    return Request("DELETE", WEBHOOKS_PATH)


def webhooks_test() -> Request:
    return Request("POST", f"{WEBHOOKS_PATH}/test")


# ---------------------------------------------------------------- Voice


def voice_access_token(platform: Optional[str] = None) -> Request:
    return Request("GET", "/api/v3/voice/access-token", query={"platform": platform})


def voice_numbers() -> Request:
    return Request("GET", "/api/v3/voice/numbers")


def calls_list(filter: Optional[str] = None, page: Optional[int] = None, per_page: Optional[int] = None) -> Request:
    return Request("GET", "/api/v3/voice/calls", query={"filter": filter, "page": page, "per_page": per_page})


def calls_get(uid: str) -> Request:
    return Request("GET", f"/api/v3/voice/calls/{_seg(uid)}")
