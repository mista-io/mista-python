from mista import APIError, Mista

with Mista() as mista:
    group = mista.contact_groups.create("Developers")

    try:
        contact = mista.contacts.create(group["uid"], phone="+1555***4567", first_name="Alice", last_name="Uwase")
        print("Added", contact["uid"])
    except APIError as error:
        print("Not added:", error.message)

    for item in mista.contacts.list(group["uid"]):
        print(item["phone"], item["first_name"])

    mista.campaigns.send_to_groups(group_uids=group["uid"], sender_id="YourBrand", message="Welcome!")
