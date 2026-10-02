from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence, Union, cast

from . import _operations as op
from ._errors import NotFoundError
from ._operations import Recipients, ScheduleTime
from .pagination import EMPTY_META, AsyncPage, Page, parse_page
from .types import (
    Account as AccountInfo,
    Balance,
    BulkCampaignResult,
    Campaign,
    CallFilter,
    Contact,
    ContactGroup,
    ContactListItem,
    GroupCampaignResult,
    SmsMessage,
    SmsType,
    Verification,
    VerificationCheck,
    VerifyChannel,
    VoiceAccessToken,
    VoiceCall,
    VoiceNumber,
)

if TYPE_CHECKING:
    from ._client import AsyncMista, Mista


def _check_result(data: Any, verified: bool) -> VerificationCheck:
    return cast(VerificationCheck, {"verified": verified, **(data or {})})


# ====================================================================== sync


class _Resource:
    def __init__(self, client: "Mista") -> None:
        self._client = client


class Sms(_Resource):
    def send(
        self,
        *,
        to: str,
        sender_id: str,
        message: str,
        type: Optional[SmsType] = None,
        media_url: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        dlt_template_id: Optional[str] = None,
    ) -> SmsMessage:
        """Send one SMS to one recipient. For several numbers or a scheduled send, use ``campaigns.bulk``."""
        return cast(
            SmsMessage,
            self._client.request(
                op.sms_send(to, sender_id, message, type, media_url, language, gender, dlt_template_id)
            ),
        )


class Campaigns(_Resource):
    def bulk(
        self,
        *,
        sender_id: str,
        recipients: Recipients,
        message: Optional[str] = None,
        type: Optional[SmsType] = None,
        name: Optional[str] = None,
        schedule_time: Optional[ScheduleTime] = None,
        dlt_template_id: Optional[str] = None,
    ) -> BulkCampaignResult:
        """Phone strings plus one ``message`` (broadcast) or ``{"to", "message"}`` dicts (personalized).
        Up to 10,000 recipients."""
        return cast(
            BulkCampaignResult,
            self._client.request(
                op.campaigns_bulk(sender_id, recipients, message, type, name, schedule_time, dlt_template_id)
            ),
        )

    def send_to_groups(
        self,
        *,
        group_uids: Union[str, Sequence[str]],
        sender_id: str,
        message: str,
        type: Optional[SmsType] = None,
        schedule_time: Optional[ScheduleTime] = None,
        dlt_template_id: Optional[str] = None,
    ) -> GroupCampaignResult:
        return cast(
            GroupCampaignResult,
            self._client.request(
                op.campaigns_send_to_groups(group_uids, sender_id, message, type, schedule_time, dlt_template_id)
            ),
        )

    def get(self, uid: str) -> Campaign:
        return cast(Campaign, self._client.request(op.campaigns_get(uid)))


class Logs(_Resource):
    def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sender_id: Optional[str] = None,
        status: Optional[str] = None,
        sms_type: Optional[SmsType] = None,
    ) -> Page[SmsMessage]:
        """Messages sent from your account. Iterate the page to walk every page."""
        filters: Dict[str, Any] = dict(
            per_page=per_page, start_date=start_date, end_date=end_date,
            sender_id=sender_id, status=status, sms_type=sms_type,
        )
        fetch = lambda n: self.list(page=n, **filters)  # noqa: E731
        try:
            raw = self._client.request(op.logs_list(page=page, **filters))
        except NotFoundError:
            return Page([], EMPTY_META, fetch)
        return Page(*parse_page(raw), fetch)

    def get(self, uid: str) -> SmsMessage:
        return cast(SmsMessage, self._client.request(op.logs_get(uid)))


class Account(_Resource):
    def balance(self) -> Balance:
        return cast(Balance, self._client.request(op.account_balance()))

    def me(self) -> AccountInfo:
        return cast(AccountInfo, self._client.request(op.account_me()))


class ContactGroups(_Resource):
    def list(self, *, page: Optional[int] = None) -> Page[ContactGroup]:
        raw = self._client.request(op.groups_list(page))
        return Page(*parse_page(raw), lambda n: self.list(page=n))

    def create(self, name: str) -> ContactGroup:
        return cast(ContactGroup, self._client.request(op.groups_create(name)))

    def get(self, group_uid: str) -> ContactGroup:
        return cast(ContactGroup, self._client.request(op.groups_get(group_uid)))

    def update(self, group_uid: str, name: str) -> ContactGroup:
        return cast(ContactGroup, self._client.request(op.groups_update(group_uid, name)))

    def delete(self, group_uid: str) -> None:
        """Deletes the group and every contact in it."""
        self._client.request(op.groups_delete(group_uid))


class Contacts(_Resource):
    def create(
        self,
        group_uid: str,
        *,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        fields: Optional[Mapping[str, str]] = None,
    ) -> Contact:
        """Add a contact. ``fields`` holds custom fields keyed by the group's field tag.
        Raises APIError if the phone is already in the group."""
        return cast(
            Contact, self._client.request(op.contacts_create(group_uid, phone, first_name, last_name, fields))
        )

    def list(self, group_uid: str, *, page: Optional[int] = None) -> Page[ContactListItem]:
        raw = self._client.request(op.contacts_list(group_uid, page))
        return Page(*parse_page(raw), lambda n: self.list(group_uid, page=n))

    def get(self, group_uid: str, uid: str) -> Contact:
        return cast(Contact, self._client.request(op.contacts_get(group_uid, uid)))

    def update(
        self,
        group_uid: str,
        uid: str,
        *,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        fields: Optional[Mapping[str, str]] = None,
    ) -> Contact:
        """``phone`` is always required; fields left out keep their current value."""
        return cast(
            Contact,
            self._client.request(op.contacts_update(group_uid, uid, phone, first_name, last_name, fields)),
        )

    def delete(self, group_uid: str, uid: str) -> None:
        self._client.request(op.contacts_delete(group_uid, uid))


class Verify(_Resource):
    def start(
        self, *, to: str, channel: Optional[VerifyChannel] = None, sender_id: Optional[str] = None
    ) -> Verification:
        """Send a one-time code. Keep the returned ``sid`` for ``check``."""
        return cast(Verification, self._client.request(op.verify_start(to, channel, sender_id)))

    def check(self, *, sid: str, code: str) -> VerificationCheck:
        """A wrong or expired code returns ``verified=False`` instead of raising."""
        try:
            data = self._client.request(op.verify_check(sid, code))
        except Exception as error:
            failed = op.failed_check(error)
            if failed is None:
                raise
            return _check_result(failed, False)
        return _check_result(data, True)

    def get(self, sid: str) -> Verification:
        return cast(Verification, self._client.request(op.verify_get(sid)))


class Calls(_Resource):
    def list(
        self, *, filter: Optional[CallFilter] = None, page: Optional[int] = None, per_page: Optional[int] = None
    ) -> Page[VoiceCall]:
        raw = self._client.request(op.calls_list(filter, page, per_page))
        return Page(*parse_page(raw), lambda n: self.list(filter=filter, page=n, per_page=per_page))

    def get(self, uid: str) -> VoiceCall:
        return cast(VoiceCall, self._client.request(op.calls_get(uid)))


class Voice(_Resource):
    def __init__(self, client: "Mista") -> None:
        super().__init__(client)
        self.calls = Calls(client)

    def access_token(self, *, platform: Optional[str] = None) -> VoiceAccessToken:
        """A short-lived Twilio Voice access token for the softphone SDKs."""
        return cast(VoiceAccessToken, self._client.request(op.voice_access_token(platform)))

    def numbers(self) -> List[VoiceNumber]:
        return cast(List[VoiceNumber], self._client.request(op.voice_numbers()))


# ===================================================================== async


class _AsyncResource:
    def __init__(self, client: "AsyncMista") -> None:
        self._client = client


class AsyncSms(_AsyncResource):
    async def send(
        self,
        *,
        to: str,
        sender_id: str,
        message: str,
        type: Optional[SmsType] = None,
        media_url: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        dlt_template_id: Optional[str] = None,
    ) -> SmsMessage:
        return cast(
            SmsMessage,
            await self._client.request(
                op.sms_send(to, sender_id, message, type, media_url, language, gender, dlt_template_id)
            ),
        )


class AsyncCampaigns(_AsyncResource):
    async def bulk(
        self,
        *,
        sender_id: str,
        recipients: Recipients,
        message: Optional[str] = None,
        type: Optional[SmsType] = None,
        name: Optional[str] = None,
        schedule_time: Optional[ScheduleTime] = None,
        dlt_template_id: Optional[str] = None,
    ) -> BulkCampaignResult:
        return cast(
            BulkCampaignResult,
            await self._client.request(
                op.campaigns_bulk(sender_id, recipients, message, type, name, schedule_time, dlt_template_id)
            ),
        )

    async def send_to_groups(
        self,
        *,
        group_uids: Union[str, Sequence[str]],
        sender_id: str,
        message: str,
        type: Optional[SmsType] = None,
        schedule_time: Optional[ScheduleTime] = None,
        dlt_template_id: Optional[str] = None,
    ) -> GroupCampaignResult:
        return cast(
            GroupCampaignResult,
            await self._client.request(
                op.campaigns_send_to_groups(group_uids, sender_id, message, type, schedule_time, dlt_template_id)
            ),
        )

    async def get(self, uid: str) -> Campaign:
        return cast(Campaign, await self._client.request(op.campaigns_get(uid)))


class AsyncLogs(_AsyncResource):
    async def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sender_id: Optional[str] = None,
        status: Optional[str] = None,
        sms_type: Optional[SmsType] = None,
    ) -> AsyncPage[SmsMessage]:
        filters: Dict[str, Any] = dict(
            per_page=per_page, start_date=start_date, end_date=end_date,
            sender_id=sender_id, status=status, sms_type=sms_type,
        )
        fetch = lambda n: self.list(page=n, **filters)  # noqa: E731
        try:
            raw = await self._client.request(op.logs_list(page=page, **filters))
        except NotFoundError:
            return AsyncPage([], EMPTY_META, fetch)
        return AsyncPage(*parse_page(raw), fetch)

    async def get(self, uid: str) -> SmsMessage:
        return cast(SmsMessage, await self._client.request(op.logs_get(uid)))


class AsyncAccount(_AsyncResource):
    async def balance(self) -> Balance:
        return cast(Balance, await self._client.request(op.account_balance()))

    async def me(self) -> AccountInfo:
        return cast(AccountInfo, await self._client.request(op.account_me()))


class AsyncContactGroups(_AsyncResource):
    async def list(self, *, page: Optional[int] = None) -> AsyncPage[ContactGroup]:
        raw = await self._client.request(op.groups_list(page))
        return AsyncPage(*parse_page(raw), lambda n: self.list(page=n))

    async def create(self, name: str) -> ContactGroup:
        return cast(ContactGroup, await self._client.request(op.groups_create(name)))

    async def get(self, group_uid: str) -> ContactGroup:
        return cast(ContactGroup, await self._client.request(op.groups_get(group_uid)))

    async def update(self, group_uid: str, name: str) -> ContactGroup:
        return cast(ContactGroup, await self._client.request(op.groups_update(group_uid, name)))

    async def delete(self, group_uid: str) -> None:
        await self._client.request(op.groups_delete(group_uid))


class AsyncContacts(_AsyncResource):
    async def create(
        self,
        group_uid: str,
        *,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        fields: Optional[Mapping[str, str]] = None,
    ) -> Contact:
        return cast(
            Contact,
            await self._client.request(op.contacts_create(group_uid, phone, first_name, last_name, fields)),
        )

    async def list(self, group_uid: str, *, page: Optional[int] = None) -> AsyncPage[ContactListItem]:
        raw = await self._client.request(op.contacts_list(group_uid, page))
        return AsyncPage(*parse_page(raw), lambda n: self.list(group_uid, page=n))

    async def get(self, group_uid: str, uid: str) -> Contact:
        return cast(Contact, await self._client.request(op.contacts_get(group_uid, uid)))

    async def update(
        self,
        group_uid: str,
        uid: str,
        *,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        fields: Optional[Mapping[str, str]] = None,
    ) -> Contact:
        return cast(
            Contact,
            await self._client.request(op.contacts_update(group_uid, uid, phone, first_name, last_name, fields)),
        )

    async def delete(self, group_uid: str, uid: str) -> None:
        await self._client.request(op.contacts_delete(group_uid, uid))


class AsyncVerify(_AsyncResource):
    async def start(
        self, *, to: str, channel: Optional[VerifyChannel] = None, sender_id: Optional[str] = None
    ) -> Verification:
        return cast(Verification, await self._client.request(op.verify_start(to, channel, sender_id)))

    async def check(self, *, sid: str, code: str) -> VerificationCheck:
        try:
            data = await self._client.request(op.verify_check(sid, code))
        except Exception as error:
            failed = op.failed_check(error)
            if failed is None:
                raise
            return _check_result(failed, False)
        return _check_result(data, True)

    async def get(self, sid: str) -> Verification:
        return cast(Verification, await self._client.request(op.verify_get(sid)))


class AsyncCalls(_AsyncResource):
    async def list(
        self, *, filter: Optional[CallFilter] = None, page: Optional[int] = None, per_page: Optional[int] = None
    ) -> AsyncPage[VoiceCall]:
        raw = await self._client.request(op.calls_list(filter, page, per_page))
        return AsyncPage(*parse_page(raw), lambda n: self.list(filter=filter, page=n, per_page=per_page))

    async def get(self, uid: str) -> VoiceCall:
        return cast(VoiceCall, await self._client.request(op.calls_get(uid)))


class AsyncVoice(_AsyncResource):
    def __init__(self, client: "AsyncMista") -> None:
        super().__init__(client)
        self.calls = AsyncCalls(client)

    async def access_token(self, *, platform: Optional[str] = None) -> VoiceAccessToken:
        return cast(VoiceAccessToken, await self._client.request(op.voice_access_token(platform)))

    async def numbers(self) -> List[VoiceNumber]:
        return cast(List[VoiceNumber], await self._client.request(op.voice_numbers()))
