"""Verify delivery report webhooks sent by Mista."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Optional, Union, cast

from ._errors import MistaError
from .types import WebhookEvent

SIGNATURE_HEADER = "Mista-Signature"
"""Name of the header that carries the webhook signature."""

DEFAULT_TOLERANCE = 300
"""Default maximum age of a webhook, in seconds."""


class WebhookVerificationError(MistaError):
    """The webhook signature is missing, malformed, too old, or does not match."""


def verify_webhook(
    payload: Union[str, bytes],
    signature_header: Optional[str],
    secret: str,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: Optional[float] = None,
) -> WebhookEvent:
    """Check the ``Mista-Signature`` header and return the parsed event.

    Pass the raw request body exactly as received (e.g. ``request.get_data()`` in Flask,
    ``await request.body()`` in FastAPI). ``tolerance=0`` disables the age check.

    Raises:
        WebhookVerificationError: if the request was not signed by Mista with this secret.
    """
    if not secret:
        raise WebhookVerificationError("Missing webhook secret")
    if not signature_header:
        raise WebhookVerificationError("Missing Mista-Signature header")

    timestamp: Optional[int] = None
    signatures = []
    for part in signature_header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise WebhookVerificationError("Malformed Mista-Signature header")

    current = time.time() if now is None else now
    if tolerance > 0 and abs(current - timestamp) > tolerance:
        raise WebhookVerificationError("Webhook timestamp is outside the tolerance window")

    body = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
    expected = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected.encode("ascii"), s.encode("utf-8")) for s in signatures):
        raise WebhookVerificationError("Webhook signature does not match")

    try:
        return cast(WebhookEvent, json.loads(body))
    except ValueError as exc:
        raise WebhookVerificationError("Webhook body is not valid JSON") from exc
