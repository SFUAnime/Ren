import logging


KEY_INSTANCE_NAME = "instanceName"
KEY_INTERVAL = "interval"
KEY_PUSH_URL = "pushUrl"

LOGGER = logging.getLogger("red.luicogs.Heartbeat")

MIN_INTERVAL = 10
MAX_FAILED_PINGS = 15

DEFAULT_GLOBAL = {KEY_INSTANCE_NAME: "Ren", KEY_INTERVAL: 295, KEY_PUSH_URL: None}
