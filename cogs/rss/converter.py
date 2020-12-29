"""
Converts v2 RSS json file to v3 format
"""
import json

UID = "5842647"  # When typed on a T9 keyboard: luicogs
BASE = {UID: {"GLOBAL": {}, "GUILD": {}}}


# In bot constants (this was changed while updating the v2 RSS)
INTERVAL = "check_interval"
CHANNEL_ID = "post_channel"
RSS_FEED_URLS = "rss_feed_urls"


V3JSON = BASE

GUILD_ID = input("Please input your server ID: ")

# Convert filter into v3 format.
with open("settings.json") as v2settings:
    print("Converting settings.json...")
    FILTERS = json.load(v2settings)
    # Creating new section for the specific guild
    V3JSON[UID]["GUILD"][GUILD_ID] = {}
    for key, val in FILTERS.items():
        # old to new name conversion
        if key == INTERVAL:
            V3JSON[UID]["GLOBAL"]["interval"] = val
        elif key == CHANNEL_ID:
            V3JSON[UID]["GUILD"][GUILD_ID]["channelId"] = val
        elif key == RSS_FEED_URLS:
            V3JSON[UID]["GUILD"][GUILD_ID]["rssFeedUrls"] = val
# writing to file using pythong json library
with open("v3data.json", "w") as output:
    json.dump(V3JSON, output, indent=4)
    print("RSS data successfully converted to v3 format!")
