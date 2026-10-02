from datetime import datetime, timedelta

from mista import Mista

with Mista() as mista:
    # Broadcast: one message to many numbers, tomorrow at 09:00 (account timezone).
    tomorrow_9am = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0)
    broadcast = mista.campaigns.bulk(
        sender_id="LOYALTY",
        recipients=["250780000001", "250780000002"],
        message="Double points this weekend!",
        schedule_time=tomorrow_9am,
    )
    print("Broadcast", broadcast["uid"], broadcast["status"])

    # Personalized: a different message per number.
    personalized = mista.campaigns.bulk(
        sender_id="LOYALTY",
        recipients=[
            {"to": "250780000001", "message": "Hi Alice, you have 120 points."},
            {"to": "250780000002", "message": "Hi Bob, you have 45 points."},
        ],
    )
    print("Personalized", personalized["uid"], personalized["recipient_count"])
