from redbot.core import checks, commands
from redbot.core.commands.context import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.hybrid_command(name="f")
    @commands.guild_only()
    async def _cmdPlusF(self, ctx: Context):
        """Pay your respects."""

        await self.cmdPlusF(ctx=ctx)

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="setf")
    @commands.guild_only()
    async def _grpSetF(self, ctx: Context):
        """Respect settings."""

    @_grpSetF.command(name="messages", aliases=["msgs"])
    @commands.guild_only()
    async def _cmdSetFMessages(self, ctx: Context, messages: int):
        """Set the number of messages that must appear before a new respect is paid.

        Parameters:
        -----------
        messages: int
            The number of messages between messages.  Should be between 1 and 100
        """

        await self.cmdSetFMessages(ctx=ctx, messages=messages)

    @_grpSetF.command(name="show")
    @commands.guild_only()
    async def _cmdSetFShow(self, ctx: Context):
        """Show the current settings."""

        await self.cmdSetFShow(ctx=ctx)

    @_grpSetF.command(name="time", aliases=["seconds"])
    @commands.guild_only()
    async def _cmdSetFTime(self, ctx: Context, seconds: int):
        """Set the number of seconds that must pass before a new respect is paid.

        Parameters:
        -----------
        seconds: int
            The number of seconds that must pass.  Should be between 1 and 100
        """

        await self.cmdSetFTime(ctx=ctx, seconds=seconds)
