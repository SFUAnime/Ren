"""Triggered cog
`triggered from spoopy.
"""

from redbot.core import commands

from .commandHandlers import CommandHandlers


class Triggered(commands.Cog, CommandHandlers):
    """We triggered, fam."""
