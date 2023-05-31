from redbot.core import commands
from redbot.core.commands import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="neural")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _groupNeural(self, ctx: Context) -> None:
        """Configure the neural cog."""

    @_groupNeural.command(name="activate")
    async def _commandNeuralActivate(self, ctx: Context) -> None:
        """Activate the neural cog for the current channel."""
        await self.commandNeuralActivate(ctx=ctx)

    @_groupNeural.command(name="deactivate")
    async def _commandNeuralDeactivate(self, ctx: Context) -> None:
        """Deactivate the neural cog for the current channel."""
        await self.commandNeuralDeactivate(ctx=ctx)
