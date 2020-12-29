#!/usr/bin/env python3.6
"""Custom v2 to v3 converter for WordFilter

Usage:
------
Copy v2 data into the same directory as this script.  This includes filter.json,
settings.json, and whitelist.json.

Outputs:
--------
Saves a converted v3 json file in the same directory with the filename v3data.json.
Original data remains untouched.
"""

import json

UID = "5842647"  # When typed on a T9 keyboard: luicogs
BASE = {UID: {"GUILD": {}}}

v3Json = BASE

# Convert filters into v3 format.
with open("filter.json") as v2Filters:
    print("Converting filter.json...")
    filters = json.load(v2Filters)
    for key, val in filters.items():
        if key not in v3Json[UID]["GUILD"]:
            v3Json[UID]["GUILD"][key] = {}
        v3Json[UID]["GUILD"][key]["filters"] = val

with open("settings.json") as v2Settings:
    print("Converting settings.json...")
    settings = json.load(v2Settings)
    for key, val in settings.items():
        if key not in v3Json[UID]["GUILD"]:
            v3Json[UID]["GUILD"][key] = {}
        # Merge two dicts together, should have no conflicts.
        v3Json[UID]["GUILD"][key] = {**v3Json[UID]["GUILD"][key], **val}

with open("whitelist.json") as v2Whitelist:
    print("Converting whitelist.json...")
    whitelist = json.load(v2Whitelist)
    for key, val in whitelist.items():
        if key not in v3Json[UID]["GUILD"]:
            v3Json[UID]["GUILD"][key] = {}
        v3Json[UID]["GUILD"][key]["channelAllowed"] = val

with open("command_blacklist.json") as v2CmdBlacklist:
    print("Converting command_blacklist.json..")
    blacklist = json.load(v2CmdBlacklist)
    for key, val in blacklist.items():
        if key not in v3Json[UID]["GUILD"]:
            v3Json[UID]["GUILD"][key] = {}
        v3Json[UID]["GUILD"][key]["commandDenied"] = val

with open("v3data.json", "w") as output:
    json.dump(v3Json, output, indent=4)
    print("Word filter data successfully converted to v3 format!")
