"""Respects cog
A replica of +f seen in another bot, except smarter..
"""

from redbot.core import commands

from .commandHandlers import CommandHandlers


class Respects(commands.Cog, CommandHandlers):
    """Pay your respects."""
