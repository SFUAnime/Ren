#!/usr/bin/env python3
"""
Converts V2 highlight data
to V3 format
"""

import json

UID = "5842647"  # When typed on a T9 keyboard: luicogs
BASE = {UID: {"MEMBER": {}}}

v3Json = BASE


# converter
with open("settings.json") as v2Highlights:
    print("Converting settings.json...")
    HIGHLIGHTS = json.load(v2Highlights)
    v3Json[UID]["MEMBER"] = HIGHLIGHTS["guilds"]


# writes the json to file
with open("v3settings.json", "w") as output:
    json.dump(v3Json, output, indent=4)
    print("Highlight data has been successfully converted to V3 format!")
