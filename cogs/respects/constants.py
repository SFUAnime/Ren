from typing import Final, List, Optional, Tuple, TypedDict


HEARTS: Final[Tuple[str, ...]] = (
    ":green_heart:",
    ":heart:",
    ":black_heart:",
    ":yellow_heart:",
    ":purple_heart:",
    ":blue_heart:",
)


# Guild-related
KEY_TIME_BETWEEN: Final[str] = "timeSinceLastRespect"
KEY_MSGS_BETWEEN: Final[str] = "msgsSinceLastRespect"
DEFAULT_TIME_BETWEEN: Final[float] = 30.0  # Time between paid respects in seconds
DEFAULT_MSGS_BETWEEN: Final[int] = 20  # The number of messages in between


class BaseGuild(TypedDict):
    timeSinceLastRespect: float
    msgsSinceLastRespect: int


BASE_GUILD: Final[BaseGuild] = {
    KEY_TIME_BETWEEN: DEFAULT_TIME_BETWEEN,
    KEY_MSGS_BETWEEN: DEFAULT_MSGS_BETWEEN,
}


# Channel-related
KEY_MSG: Final[str] = "msg"
KEY_TIME: Final[str] = "time"
KEY_USERS: Final[str] = "users"


class BaseChannel(TypedDict):
    msg: Optional[int]
    time: Optional[float]
    users: List[int]


BASE_CHANNEL: Final[BaseChannel] = {
    KEY_MSG: None,
    KEY_TIME: None,
    KEY_USERS: [],
}
