import discord

import aiohttp
import asyncio  # Used for task loop.
from datetime import datetime
import logging

from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

KEY_INSTANCE_NAME = "instanceName"
KEY_INTERVAL = "interval"
KEY_PUSH_URL = "pushUrl"

LOGGER = logging.getLogger("red.luicogs.Heartbeat")

MIN_INTERVAL = 10
MAX_FAILED_PINGS = 15

DEFAULT_GLOBAL = {KEY_INSTANCE_NAME: "Ren", KEY_INTERVAL: 295, KEY_PUSH_URL: None}


class Heartbeat(commands.Cog):
    """Heartbeat for uptime checks"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_global(**DEFAULT_GLOBAL)
        self.bgTask = self.bot.loop.create_task(self._loop())

    async def _loop(self):
        session = aiohttp.ClientSession()
        initialInterval = await self.config.get_attr(KEY_INTERVAL)()
        LOGGER.info("Heartbeat is running, pinging at %s second intervals", initialInterval)

        countFailedPings = 0
        # the following loop shall break only on cancel event
        # and shall keep running on other exceptions until exceeding
        # the threshold for failed retries
        while self == self.bot.get_cog("Heartbeat"):
            try:
                await asyncio.sleep(await self.config.get_attr(KEY_INTERVAL)())
                url = await self.config.get_attr(KEY_PUSH_URL)()
                if url:
                    LOGGER.debug("Pinging %s", url)
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            # reset failed count to zero on success
                            LOGGER.debug("Successfully pinged %s", url)
                            countFailedPings = 0
                        else:
                            # increment failed count
                            LOGGER.error("HTTP GET failed! We got HTTP code %s", resp.status)
                            countFailedPings += 1
            except asyncio.CancelledError:
                # cancelled
                LOGGER.error(
                    "The background task got cancelled! If the cog was reloaded, "
                    "this can be safely ignored",
                    exc_info=True,
                )
                break
            except Exception:
                # keep retrying
                LOGGER.error("Something went wrong!", exc_info=True)
                countFailedPings += 1
            except:
                # these abnormal exceptions should not happen
                LOGGER.error("Something went horribly wrong!", exc_info=True)
                break

            if countFailedPings > 0:
                if countFailedPings <= MAX_FAILED_PINGS:
                    LOGGER.debug(
                        "Retrying in %d seconds... (attempt %d of %d)",
                        await self.config.get_attr(KEY_INTERVAL)(),
                        countFailedPings,
                        MAX_FAILED_PINGS,
                    )
                else:
                    LOGGER.error(
                        "Heartbeat main loop stopped after exceeding %d failed attempts",
                        MAX_FAILED_PINGS,
                    )
                    break

        # the session has to be closed
        if not session.closed:
            await session.close()

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        LOGGER.info("Cancelling heartbeat")
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()

    @commands.command(name="heartbeat", aliases=["hb"])
    @commands.guild_only()
    async def _check(self, ctx: Context):
        name = await self.config.get_attr(KEY_INSTANCE_NAME)()
        await ctx.send(f"**{name}** is responding.")

    @commands.group(name="heartbeatset", aliases=["hbset"])
    @checks.is_owner()
    async def hbSettings(self, ctx: Context):
        """Configure heartbeat settings."""

    @hbSettings.command(name="url")
    async def url(self, ctx: Context, url: str):
        """Set the push URL to notify

        Parameters:
        -----------
        str: url
            The URL to notify.
        """
        await self.config.get_attr(KEY_PUSH_URL).set(url)
        await ctx.send(f"Set the push URL to: `{url}`")

    @hbSettings.command(name="interval")
    async def interval(self, ctx: Context, interval: int):
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

    @hbSettings.command(name="name")
    async def name(self, ctx: Context, name: str):
        """Set the instance name.

        This is used to display when you run the heartbeat command from the bot.

        Parameters:
        -----------
        name: str
            The instance name.
        """
        await self.config.get_attr(KEY_INSTANCE_NAME).set(name)
        await ctx.send(f"Set the instance name to: `{name}`")
