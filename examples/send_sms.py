"""MISTA_API_TOKEN=... python examples/send_sms.py '+1555***4567'"""

import sys

from mista import Mista

with Mista() as mista:
    message = mista.sms.send(to=sys.argv[1], sender_id="YourBrand", message="Hello from Mista")
    print("Queued", message["uid"])
    print("Status", mista.logs.get(message["uid"])["status"])
