# Mista Python SDK

Official Python client for the [Mista](https://mista.io) Messaging, Verify and Voice APIs.
Full API reference: https://docs.mista.io

```bash
pip install mista
```

Requires Python 3.9+. The only dependency is [httpx](https://www.python-httpx.org/).
Both a synchronous (`Mista`) and an asynchronous (`AsyncMista`) client are included.

## Quickstart

```python
from mista import Mista

mista = Mista(token="...")  # or set MISTA_API_TOKEN

message = mista.sms.send(to="250780000001", sender_id="YourBrand", message="Your order has shipped")
print(message["uid"], message["status"])
```

Get your API token in the dashboard under **Settings → API**. Responses are plain dicts with the
same snake_case keys as the docs (typed as `TypedDict`s in `mista.types`).

Async:

```python
import asyncio
from mista import AsyncMista

async def main() -> None:
    async with AsyncMista() as mista:
        balance = await mista.account.balance()
        print(balance["remaining_unit"])

asyncio.run(main())
```

Every method below works the same way on `AsyncMista`; just `await` it.

## SMS

`sms.send` sends one message to **one** recipient. To reach several numbers, or to schedule a
send, use a campaign.

```python
message = mista.sms.send(
    to="250780000001",
    sender_id="YourBrand",
    message="Hello",
    type="plain",  # plain | unicode | voice | mms | whatsapp | viber | otp
)
latest = mista.logs.get(message["uid"])  # delivery status
```

## Campaigns

```python
from datetime import datetime

# Broadcast: one message, up to 10,000 numbers
mista.campaigns.bulk(
    sender_id="LOYALTY",
    recipients=["250780000001", "250780000002"],
    message="Double points this weekend!",
    schedule_time=datetime(2026, 12, 24, 9, 0),  # or "2026-12-24 09:00"; account timezone
)

# Personalized: one message per number
mista.campaigns.bulk(
    sender_id="LOYALTY",
    recipients=[
        {"to": "250780000001", "message": "Hi Alice, you have 120 points."},
        {"to": "250780000002", "message": "Hi Bob, you have 45 points."},
    ],
)

# Everyone in one or more contact groups
mista.campaigns.send_to_groups(group_uids=["grp_uid"], sender_id="YourBrand", message="Hi!")

campaign = mista.campaigns.get("campaign_uid")
```

## Message logs

```python
page = mista.logs.list(start_date="2026-10-01", status="Delivered", per_page=50)
page.items        # this page
page.meta.total   # total matches

for message in page:  # walks every remaining page (use `async for` with AsyncMista)
    print(message["uid"], message["status"])
```

Filters: `page`, `per_page`, `start_date`, `end_date` (`Y-m-d`), `sender_id`, `status`, `sms_type`.
When nothing matches, you get an empty page.

## Account

```python
balance = mista.account.balance()  # {"remaining_unit": ..., "expired_on": ...}
me = mista.account.me()
```

## Contact groups and contacts

```python
group = mista.contact_groups.create("Developers")
mista.contact_groups.list()
mista.contact_groups.get(group["uid"])
mista.contact_groups.update(group["uid"], "Developers KGL")

contact = mista.contacts.create(
    group["uid"],
    phone="250780000001",
    first_name="Alice",
    last_name="Uwase",
    fields={"CITY": "Kigali"},  # custom fields, keyed by the group's field tag
)
mista.contacts.list(group["uid"])
mista.contacts.get(group["uid"], contact["uid"])
mista.contacts.update(group["uid"], contact["uid"], phone="250780000001", first_name="Alicia")
mista.contacts.delete(group["uid"], contact["uid"])

mista.contact_groups.delete(group["uid"])  # also deletes its contacts
```

## Verify (OTP)

```python
verification = mista.verify.start(to="+250780000001", channel="sms")

result = mista.verify.check(sid=verification["sid"], code="123456")
if result["verified"]:
    ...  # signed in
else:
    print(result["reason"])  # e.g. "invalid_code"; a wrong code does not raise

mista.verify.get(verification["sid"])
```

## Voice

```python
token = mista.voice.access_token(platform="ios")["token"]
numbers = mista.voice.numbers()
calls = mista.voice.calls.list(filter="missed", per_page=20)
call = mista.voice.calls.get("call_uid")
```

## Errors

Every failure raises a subclass of `mista.MistaError`:

| Exception | When |
| --- | --- |
| `BadRequestError` | 400, e.g. an invalid phone number |
| `AuthenticationError` | 401, missing or wrong token |
| `PermissionDeniedError` | 403 |
| `NotFoundError` | 404 |
| `ValidationError` | 422; field problems are in `error.errors` |
| `RateLimitError` | 429 after retries; see `error.retry_after` |
| `ServerError` | 5xx |
| `APIError` | any other API error, including a 200 whose body says `"status": "error"` (e.g. a contact already in the group) |
| `APIConnectionError` / `APITimeoutError` | network failure or timeout |

```python
from mista import ValidationError

try:
    mista.sms.send(to="123", sender_id="YourBrand", message="Hi")
except ValidationError as error:
    for problem in error.errors:
        print(problem.field, problem.message)
```

All API errors carry `status`, `body` (the parsed response) and `headers`.

## Retries, timeouts and HTTP client

```python
mista = Mista(max_retries=2, timeout=30.0)
```

- `429 Too Many Requests` is retried for every request, waiting for `Retry-After`.
- Network errors and 5xx responses are retried for `GET` only, so a send is never duplicated.
- `max_retries=0` turns retries off.
- Pass `http_client=httpx.Client(...)` (or `httpx.AsyncClient`) for proxies or custom transports.
- Use the client as a context manager, or call `close()` / `await aclose()`, to release connections.

## Not covered

Delivery-report webhooks (configure those in the dashboard) and the retired Push API.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest && .venv/bin/mypy
MISTA_API_TOKEN=... .venv/bin/python scripts/smoke.py   # read-only: balance + account
```

## License

MIT
