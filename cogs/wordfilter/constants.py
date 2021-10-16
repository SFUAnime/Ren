from discord import Colour

COLOUR = Colour
COLOURS = [COLOUR.purple(), COLOUR.red(), COLOUR.blue(), COLOUR.orange(), COLOUR.green()]

KEY_CHANNEL_IDS = "channelIdsAllowed"
KEY_FILTERS = "filters"
KEY_CMD_DENIED = "commandDenied"
KEY_TOGGLE_MOD = "toggleMod"
KEY_USAGE_STATS = "usageStats"
BASE = {
    KEY_CHANNEL_IDS: [],
    KEY_FILTERS: [],
    KEY_CMD_DENIED: [],
    KEY_TOGGLE_MOD: False,
    KEY_USAGE_STATS: {},
}
