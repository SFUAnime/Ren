from typing import Dict, Final, TypedDict

SYSTEM_MESSAGE_STR: Final[str] = "SYSTEM"
COMMAND_FILTER_CUTOFF: Final[int] = 24  # Chars
BASE_TYPING_WAIT: Final[int] = 6  # Seconds
INIT_CHAT_HISTORY_LIMIT: Final[int] = 30  # Messages
INBOUND_BUFFER_CHAR_LIMIT: Final[int] = 1024
OLD_CHAT_HISTORY_CHAR_LIMIT: Final[int] = 512


# LLM API
LLM_API_BASE: Final[str] = "http://localhost:8000/v1"
LLM_API_KEY: Final[str] = "renrenren"  # No auth implemented, any random string works
LLM_API_PRESENCE_PENALTY: Final[float] = 1.17647


# Chances to start chat
KEY_AT_MENTION_START: Final[str] = "atMentionStart"
KEY_CASUAL_MENTION_START: Final[str] = "casualMentionStart"
KEY_SELF_START: Final[str] = "selfStart"
CHAT_START_CHANCE: Final[Dict[str, float]] = {
    KEY_AT_MENTION_START: 1.0,
    KEY_CASUAL_MENTION_START: 0.5,
    KEY_SELF_START: 0.01,
}


# Chances to follow up after her own message during a chat
LONG_MESSAGE_CUTOFF: Final[int] = 32  # Chars

KEY_QUESTION_FOLLOW_UP: Final[str] = "question"
KEY_LONG_MESSAGE_FOLLOW_UP: Final[str] = "longMessage"
KEY_BASE_FOLLOW_UP: Final[str] = "baseChance"
FOLLOW_UP_CHANCE: Final[Dict[str, float]] = {
    KEY_QUESTION_FOLLOW_UP: 0.01,
    KEY_LONG_MESSAGE_FOLLOW_UP: 0.1,
    KEY_BASE_FOLLOW_UP: 0.7,
}


# Chances to end chat
CHAT_HISTORY_CHAR_LIMIT: Final[int] = 3072  # Lazy token estimate, do it properly later
STALE_CHAT_PERIOD: Final[int] = 900  # Seconds

KEY_TOKEN_LIMIT_END: Final[str] = "tokenLimitEnd"
KEY_STALE_CHAT_END: Final[str] = "staleChatEnd"
KEY_SELF_END: Final[str] = "selfEnd"
CHAT_END_CHANCE: Final[Dict[str, float]] = {
    KEY_TOKEN_LIMIT_END: 1.0,
    KEY_STALE_CHAT_END: 0.5,
    KEY_SELF_END: 0.01,
}


# Channel config
KEY_NEURAL_ACTIVE: Final[str] = "neuralActive"


class BaseChannel(TypedDict):
    neuralActive: bool


BASE_CHANNEL: Final[BaseChannel] = {
    KEY_NEURAL_ACTIVE: False,
}
