"""YOURLS module

Control Your Own URL Shortener instance.
"""

from redbot.core import commands

from .commandHandlers import CommandHandlers


class YOURLS(commands.Cog, CommandHandlers):
    """Manage Your Own URL Shortener (YOURLS) from Discord."""
