from redbot.core import commands

from .commandHandlers import CommandHandlers


class SlashSync(commands.Cog, CommandHandlers):
    """Synchronize slash commands on the bot to Discord"""
