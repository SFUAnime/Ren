from redbot.core import checks, commands
from redbot.core.commands import Context

from .commandsCore import SlashSyncCommandsCore


class SlashSyncCommandHandlers(SlashSyncCommandsCore):
    @commands.command(name="sync")
    @checks.is_owner()
    async def _cmdSync(self, ctx: Context):
        await self.cmdSync(ctx)
