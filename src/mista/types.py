"""Response shapes. Responses are plain dicts with the same snake_case keys as https://docs.mista.io."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict, Union

SmsType = Literal["plain", "unicode", "voice", "mms", "whatsapp", "viber", "otp"]
VerifyChannel = Literal["auto", "sms", "whatsapp", "whatsapp_sms", "sms_whatsapp", "whatsapp_only"]
CallFilter = Literal["all", "inbound", "outbound", "missed"]


class PersonalizedRecipient(TypedDict):
    to: str
    message: str


SmsMessage = TypedDict(
    "SmsMessage",
    {
        "uid": str,
        "to": str,
        "from": str,
        "message": str,
        "status": str,
        "cost": Union[str, float],
        "sms_type": str,
        "direction": str,
        "send_by": str,
        "created_at": str,
        "updated_at": str,
    },
    total=False,
)


class BulkCampaignResult(TypedDict):
    uid: str
    campaign_name: str
    status: str
    recipient_count: int
    mode: Literal["broadcast", "personalized"]


class GroupCampaignResult(TypedDict):
    uid: str
    campaign_name: str
    status: str


class Campaign(TypedDict, total=False):
    id: str
    name: str
    message: str
    status: str
    type: str
    created_at: str
    start_at: Optional[str]
    delivery_at: Optional[str]
    stats: Dict[str, int]


class Balance(TypedDict, total=False):
    remaining_unit: str
    expired_on: str
    airtime_balance: str
    airtime_currency: str


class Account(TypedDict, total=False):
    uid: str
    api_token: str
    first_name: str
    last_name: str
    email: str
    locale: str
    timezone: str
    last_access_at: Optional[str]


class ContactGroup(TypedDict):
    uid: str
    name: str


class Contact(TypedDict, total=False):
    uid: str
    phone: Union[str, int]
    status: str
    custom_fields: Dict[str, str]


class ContactListItem(TypedDict, total=False):
    uid: str
    phone: Union[str, int]
    first_name: Optional[str]
    last_name: Optional[str]


class Verification(TypedDict, total=False):
    sid: str
    to: str
    channel: str
    status: str
    expires_at: Optional[str]
    check_attempts: int
    verified_at: Optional[str]
    created_at: Optional[str]


class VerificationCheck(TypedDict, total=False):
    verified: bool
    """True when the code was correct. A wrong or expired code is returned, not raised."""
    sid: str
    status: str
    verified_at: Optional[str]
    reason: str
    """Why the check failed, e.g. ``"invalid_code"`` or ``"expired"``."""


class VoiceAccessToken(TypedDict, total=False):
    token: str
    identity: str
    caller_id: Optional[str]
    account_sid: str
    twiml_app_sid: str


class VoiceNumber(TypedDict, total=False):
    uid: str
    number: str
    capabilities: List[str]
    provider: str
    voice: bool
    status: str


VoiceCall = TypedDict(
    "VoiceCall",
    {
        "uid": str,
        "direction": Literal["inbound", "outbound"],
        "from": str,
        "to": str,
        "status": str,
        "is_active": bool,
        "duration": Optional[int],
        "recording_url": Optional[str],
        "recording_duration": Optional[int],
        "started_at": Optional[str],
        "ended_at": Optional[str],
        "created_at": Optional[str],
    },
)
