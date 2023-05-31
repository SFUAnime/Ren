from redbot.core import commands

from .commandHandlers import CommandHandlers
from .eventHandlers import EventHandlers


class Neural(commands.Cog, CommandHandlers, EventHandlers):
    """Neural net-driven chatbot."""
