# Changelog

## 0.2.0

- Delivery report webhooks: `webhooks.get`, `webhooks.set`, `webhooks.delete`, `webhooks.test`
  (sync and async).
- `verify_webhook(raw_body, signature_header, secret)` checks the `Mista-Signature` header and
  returns the typed event; raises `WebhookVerificationError`.
- Message `status` is now typed as `MessageStatus` (Queued, Sent, Delivered, Undelivered, Expired,
  Rejected, Failed) and messages carry `status_detail`. The API no longer returns gateway references
  such as `Sent|ATXid_...`.

## 0.1.0

First release, covering the Mista API v3 as documented at https://docs.mista.io,
with a synchronous `Mista` and an asynchronous `AsyncMista` client:

- SMS: `sms.send`
- Campaigns: `campaigns.bulk`, `campaigns.send_to_groups`, `campaigns.get`
- Logs: `logs.list` (filters + auto-pagination), `logs.get`
- Account: `account.balance`, `account.me`
- Contact groups and contacts: list, create, get, update, delete
- Verify: `verify.start`, `verify.check`, `verify.get`
- Voice: `voice.access_token`, `voice.numbers`, `voice.calls.list`, `voice.calls.get`
- Typed errors, automatic retries for rate limits, request timeouts, `py.typed`
