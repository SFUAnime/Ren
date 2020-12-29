from discord import PermissionOverwrite

KEY_SETTINGS = "settings"
KEY_ARCHIVE = "archive"
KEY_CH_ID = "channel"
KEY_CH_TOPIC = "channelTopic"
KEY_CH_NAME = "channelName"
KEY_CH_POS = "channelPosition"
KEY_CH_CREATED = "channelCreated"
KEY_CH_CATEGORY = "channelCategory"
KEY_DURATION_HOURS = "durationHours"
KEY_DURATION_MINS = "durationMinutes"
KEY_START_HOUR = "startHour"
KEY_START_MIN = "startMinute"
KEY_STOP_TIME = "stopTime"
KEY_ENABLED = "enabled"
KEY_NSFW = "nsfw"
KEY_ROLE_ALLOW = "roleAllow"
KEY_ROLE_DENY = "roleDeny"

KEYS_REQUIRED = [
    KEY_CH_ID,
    KEY_CH_TOPIC,
    KEY_CH_NAME,
    KEY_CH_POS,
    KEY_CH_CREATED,
    KEY_CH_CATEGORY,
    KEY_DURATION_HOURS,
    KEY_DURATION_MINS,
    KEY_START_HOUR,
    KEY_START_MIN,
    KEY_ENABLED,
    KEY_NSFW,
    KEY_ROLE_ALLOW,
    KEY_ROLE_DENY,
]

MAX_CH_NAME = 25
MAX_CH_POS = 100
MAX_CH_TOPIC = 1024

PERMS_READ_Y = PermissionOverwrite(read_messages=True, add_reactions=False)
PERMS_READ_N = PermissionOverwrite(read_messages=False, add_reactions=False)
PERMS_SEND_N = PermissionOverwrite(send_messages=False, add_reactions=False)

SLEEP_TIME = 15  # Background loop sleep time in seconds


DEFAULT_GUILD = {
    KEY_ARCHIVE: False,
    KEY_CH_ID: None,
    KEY_CH_NAME: "temp-channel",
    KEY_CH_TOPIC: "Created with the TempChannels cog!",
    KEY_CH_POS: 0,
    KEY_CH_CREATED: False,
    KEY_CH_CATEGORY: 0,
    KEY_DURATION_HOURS: 0,
    KEY_DURATION_MINS: 1,
    KEY_START_HOUR: 20,
    KEY_START_MIN: 0,
    KEY_ENABLED: False,
    KEY_NSFW: False,
    KEY_ROLE_ALLOW: [],
    KEY_ROLE_DENY: [],
}
