#!/usr/bin/env python3.7
"""Custom v2 to v3 converter for Birthday.

Usage:
------
Copy the v2 settings.json file into the same directory as this script.

Outputs:
--------
Saves a converted v3 json file in the same directory with the filename v3data.json.
Original data remains untouched.
"""

import json

KEY_BDAY_ROLE = "birthdayRole"
KEY_BDAY_USERS = "birthdayUsers"
UID = "5842647"  # When typed on a T9 keyboard: luicogs
BASE = {UID: {"GUILD": {}, "MEMBER": {}}}

v3Json = BASE

# Convert settings into v3 format.
with open("settings.json") as v2Settings:
    print("Converting settings.json...")
    settings = json.load(v2Settings)
    for key, val in settings.items():
        if key not in v3Json[UID]["GUILD"]:
            v3Json[UID]["GUILD"][key] = {}
        if key not in v3Json[UID]["MEMBER"]:
            v3Json[UID]["MEMBER"][key] = {}

        v3Json[UID]["GUILD"][key][KEY_BDAY_ROLE] = settings[key][KEY_BDAY_ROLE]
        v3Json[UID]["MEMBER"][key] = settings[key][KEY_BDAY_USERS]

with open("v3data.json", "w") as output:
    json.dump(v3Json, output, indent=4)
    print("Birthday data successfully converted to v3 format!")
