from abc import ABC
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context


class SFUMeta(type(commands.Cog), type(ABC)):
    """Meta class for inheritance"""


class SFUBase(commands.Cog, metaclass=SFUMeta):
    """Base class containing only the SFU group command"""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.group(name="sfu")
    @commands.guild_only()
    async def sfuGroup(self, ctx: Context):
        """Access SFU-related resources"""
