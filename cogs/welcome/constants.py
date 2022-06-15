from enum import IntEnum

KEY_DM_ENABLED = "dmEnabled"
KEY_LOG_JOIN_ENABLED = "logJoinEnabled"
KEY_LOG_JOIN_CHANNEL = "logJoinChannel"
KEY_LOG_LEAVE_ENABLED = "logLeaveEnabled"
KEY_LOG_LEAVE_CHANNEL = "logLeaveChannel"
KEY_TITLE = "title"
KEY_MESSAGE = "message"
KEY_IMAGE = "image"
KEY_GREETINGS = "greetings"
KEY_RETURNING_GREETINGS = "returningGreetings"
KEY_WELCOME_CHANNEL = "welcomeChannel"
KEY_WELCOME_CHANNEL_ENABLED = "welcomeChannelSet"
KEY_DESCRIPTIONS = "descriptions"
KEY_WELCOME_CHANNEL_SETTINGS = "welcomeChannelSettings"
KEY_POST_FAILED_DM = "postFailedDm"
KEY_JOINED_USER_IDS = "joinedUserIds"

MAX_MESSAGE_LENGTH = 2000
MAX_DESCRIPTION_LENGTH = 500

DEFAULT_GUILD = {
    KEY_DM_ENABLED: False,
    KEY_LOG_JOIN_ENABLED: False,
    KEY_LOG_JOIN_CHANNEL: None,
    KEY_LOG_LEAVE_ENABLED: False,
    KEY_LOG_LEAVE_CHANNEL: None,
    KEY_TITLE: "Welcome!",
    KEY_MESSAGE: "Welcome to the server! Hope you enjoy your stay!",
    KEY_IMAGE: None,
    KEY_GREETINGS: {},
    KEY_RETURNING_GREETINGS: {},
    KEY_WELCOME_CHANNEL: None,
    KEY_WELCOME_CHANNEL_ENABLED: False,
    KEY_DESCRIPTIONS: {},
    KEY_WELCOME_CHANNEL_SETTINGS: {
        KEY_POST_FAILED_DM: False,
    },
    KEY_JOINED_USER_IDS: [],
}


class GreetingPools(IntEnum):
    DEFAULT = 0
    RETURNING = 1
