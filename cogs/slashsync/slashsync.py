from redbot.core import commands

from .commandHandlers import SlashSyncCommandHandlers


class SlashSync(commands.Cog, SlashSyncCommandHandlers):
    """Synchronize slash commands on the bot to Discord"""
