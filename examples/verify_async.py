import asyncio

from mista import AsyncMista


async def main() -> None:
    async with AsyncMista() as mista:
        verification = await mista.verify.start(to="+250780000001", channel="sms")
        print("Code sent, sid", verification["sid"])

        code = input("Code: ")
        result = await mista.verify.check(sid=verification["sid"], code=code)
        print("Verified" if result["verified"] else f"Rejected: {result.get('reason')}")


asyncio.run(main())
