import discord

from redbot.core import commands
from redbot.core.commands import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.hybrid_command(name="triggered")
    async def _cmdTriggered(self, ctx: Context, user: discord.User = None):
        await self.cmdTriggered(ctx=ctx, user=user)

    @commands.hybrid_command(name="reallytriggered")
    async def _cmdHypertriggered(self, ctx: Context, user: discord.User = None):
        await self.cmdHypertriggered(ctx=ctx, user=user)

    @commands.hybrid_command(name="hypertriggered")
    async def _cmdDeepfry(self, ctx: Context, user: discord.User = None):
        await self.cmdDeepfry(ctx=ctx, user=user)
