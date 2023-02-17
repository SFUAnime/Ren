"""Server Manage Cog, to help manage server icon and banners."""
from redbot.core import commands

from .commandHandlers import CommandHandlers


class ServerManage(commands.Cog, CommandHandlers):
    """Auto-assign server banner and icon on configurable days."""
