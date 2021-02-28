from abc import ABC

from redbot.core import commands
from redbot.core.commands.context import Context

from .meta import SFUMeta
from .roads import SFURoads
from .courses import SFUCourses


class SFUBase(commands.Cog, metaclass=SFUMeta):
    """Base class containing only the SFU group command"""

    @commands.group(name="sfu")
    @commands.guild_only()
    async def sfuGroup(self, ctx: Context):
        """Access SFU-related resources."""


class SFU(SFUCourses, SFURoads, SFUBase, commands.Cog, metaclass=SFUMeta):
    """SFU resources on Discord."""
