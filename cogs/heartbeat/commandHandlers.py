from redbot.core import checks, commands
from redbot.core.commands.context import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.command(name="heartbeat", aliases=["hb"])
    @commands.guild_only()
    async def _cmdCheck(self, ctx: Context):
        await self.cmdCheck(ctx=ctx)

    @commands.group(name="heartbeatset", aliases=["hbset"])
    @checks.is_owner()
    async def _grpHbSettings(self, ctx: Context):
        """Configure heartbeat settings."""

    @_grpHbSettings.command(name="url")
    async def _cmdUrl(self, ctx: Context, url: str):
        """Set the push URL to notify

        Parameters:
        -----------
        str: url
            The URL to notify.
        """
        await self.cmdUrl(ctx=ctx, url=url)

    @_grpHbSettings.command(name="interval")
    async def _cmdInterval(self, ctx: Context, interval: int):
        """Set the heartbeat interval.

        Parameters:
        -----------
        interval: int
            The interval time in seconds.
        """
        await self.cmdInterval(ctx=ctx, interval=interval)

    @_grpHbSettings.command(name="name")
    async def _cmdName(self, ctx: Context, name: str):
        """Set the instance name.

        This is used to display when you run the heartbeat command from the bot.

        Parameters:
        -----------
        name: str
            The instance name.
        """
        await self.cmdName(ctx=ctx, name=name)
