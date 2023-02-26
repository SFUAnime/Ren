from redbot.core.commands.context import Context

from .core import Core
from .constants import KEY_INSTANCE_NAME, KEY_INTERVAL, KEY_PUSH_URL, MIN_INTERVAL


class CommandsCore(Core):
    async def cmdCheck(self, ctx: Context):
        name = await self.config.get_attr(KEY_INSTANCE_NAME)()
        await ctx.send(f"**{name}** is responding.")

    async def cmdUrl(self, ctx: Context, url: str):
        """Set the push URL to notify

        Parameters:
        -----------
        str: url
            The URL to notify.
        """
        await self.config.get_attr(KEY_PUSH_URL).set(url)
        await ctx.send(f"Set the push URL to: `{url}`")

    async def cmdInterval(self, ctx: Context, interval: int):
        """Set the heartbeat interval.

        Parameters:
        -----------
        interval: int
            The interval time in seconds.
        """
        if interval < MIN_INTERVAL:
            await ctx.send(f"Please set an interval greater than **{MIN_INTERVAL}** seconds")
            return
        await self.config.get_attr(KEY_INTERVAL).set(interval)
        await ctx.send(f"Set interval to: `{interval}` seconds")

    async def cmdName(self, ctx: Context, name: str):
        """Set the instance name.

        This is used to display when you run the heartbeat command from the bot.

        Parameters:
        -----------
        name: str
            The instance name.
        """
        await self.config.get_attr(KEY_INSTANCE_NAME).set(name)
        await ctx.send(f"Set the instance name to: `{name}`")
