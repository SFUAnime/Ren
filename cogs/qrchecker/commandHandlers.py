from redbot.core import commands
from redbot.core.commands import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="qrchecker")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _grpQrChecker(self, ctx: Context):
        """Configure QR code checker"""

    @_grpQrChecker.command(name="toggle")
    async def _cmdQrCheckerToggle(self, ctx: Context):
        await self.cmdQrCheckerToggle(ctx=ctx)
