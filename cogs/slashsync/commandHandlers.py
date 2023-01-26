from redbot.core import checks, commands
from redbot.core.commands import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.command(name="sync")
    @checks.is_owner()
    async def _cmdSync(self, ctx: Context):
        await self.cmdSync(ctx)
