from datetime import timedelta


KEY_USERS = "users"
KEY_TIME = "time"
KEY_MSG = "msg"
KEY_TIME_BETWEEN = "timeSinceLastRespect"
KEY_MSGS_BETWEEN = "msgsSinceLastRespect"
HEARTS = [
    ":green_heart:",
    ":heart:",
    ":black_heart:",
    ":yellow_heart:",
    ":purple_heart:",
    ":blue_heart:",
]
DEFAULT_TIME_BETWEEN = timedelta(seconds=30)  # Time between paid respects.
DEFAULT_MSGS_BETWEEN = 20  # The number of messages in between

BASE_GUILD = {KEY_TIME_BETWEEN: 30, KEY_MSGS_BETWEEN: 20}
BASE_CHANNEL = {KEY_MSG: None, KEY_TIME: None, KEY_USERS: []}
