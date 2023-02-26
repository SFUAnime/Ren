from redbot.core import commands

from .commandHandlers import CommandHandlers


class Heartbeat(commands.Cog, CommandHandlers):
    """Heartbeat for uptime checks"""
