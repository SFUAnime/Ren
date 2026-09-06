"""Birthday cog Automatically add users to a specified birthday role on their
birthday."""

from redbot.core import commands

from .commandHandlers import CommandHandlers


class Birthday(commands.Cog, CommandHandlers):
    """Adds a role to someone on their birthday, and automatically remove them
    from this role after the day is over."""
