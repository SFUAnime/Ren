import re
from typing import Iterable, List, Union

from discord import Message

from redbot.core.bot import Red

from .constants import COMMAND_FILTER_CUTOFF


async def isProbablyCommand(bot: Red, message: Message) -> bool:
    """Return whether the message is likely a prefix command for this bot."""

    if len(message.content) > COMMAND_FILTER_CUTOFF:
        return False
    if isCasualMention(bot.user.display_name, message):
        return False

    commandPrefixes: Union[Iterable[str], str]
    if callable(bot.command_prefix):
        commandPrefixes = await bot.command_prefix(bot, message)
    else:
        commandPrefixes = bot.command_prefix

    if isinstance(commandPrefixes, str):
        if message.content.startswith(commandPrefixes):
            return True
    for prefix in commandPrefixes:
        if message.content.startswith(prefix):
            return True
    return False


def isAtMention(name: str, message: Message) -> bool:
    """Return whether the name is @mentioned in the message."""
    for mention in message.mentions:
        if mention.name == name:
            return True
    return False


def isCasualMention(name: str, message: Message) -> bool:
    """Return whether the name is casually mentioned in the message."""
    cleanedWordList: List[str] = re.sub(r"[,.]", "", message.content).lower().split()
    nameParts: List[str] = name.lower().split()
    for part in nameParts:
        if part in cleanedWordList:
            return True
    return False
