"""Read-only check against the live API. Never sends messages.

MISTA_API_TOKEN=... python scripts/smoke.py
"""

import os
import sys

from mista import Mista

if not os.environ.get("MISTA_API_TOKEN"):
    print("MISTA_API_TOKEN is not set; skipping live smoke test.")
    sys.exit(0)

with Mista() as mista:
    balance = mista.account.balance()
    print("balance:", balance.get("remaining_unit"), "expires", balance.get("expired_on"))
    me = mista.account.me()
    print("account:", me.get("email"), me.get("timezone"))
