import discord

import asyncio  # Used for task loop.
import os  # Used to create folder at first load.
from datetime import datetime
import logging
import requests

from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

KEY_INSTANCE_NAME = "instanceName"
KEY_INTERVAL = "interval"
KEY_PUSH_URL = "pushUrl"

LOGGER = logging.getLogger("red.luicogs.Heartbeat")

MIN_INTERVAL = 10

DEFAULT_GLOBAL = {KEY_INSTANCE_NAME: "Ren", KEY_INTERVAL: 295, KEY_PUSH_URL: None}


class Heartbeat(commands.Cog):
    """Heartbeat for uptime checks"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.time_interval = 295
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_global(**DEFAULT_GLOBAL)
        self.bgTask = self.bot.loop.create_task(self._loop())

    async def _loop(self):
        LOGGER.info("Heartbeat is running, pinging at %s second intervals", self.time_interval)
        while self == self.bot.get_cog("Heartbeat"):
            try:
                await asyncio.sleep(await self.config.interval())
                if await self.config.pushUrl():
                    LOGGER.debug("Pinging %s", await self.config.pushUrl())
                    requests.get(await self.config.pushUrl())
            except asyncio.CancelledError as e:
                LOGGER.error("Error in sleeping")
                raise e
            except requests.exceptions.HTTPError as error:
                LOGGER.error("HTTP error occurred: %s", error)

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        LOGGER.info("Cancelling heartbeat")
        self.bgTask.cancel()

    @commands.command(name="heartbeat", aliases=["hb"])
    @commands.guild_only()
    async def _check(self, ctx: Context):
        name = await self.config.instanceName()
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
        await self.config.pushUrl.set(url)
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
        await self.config.interval.set(interval)
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
        await self.config.instanceName.set(name)
        await ctx.send(f"Set the instance name to: `{name}`")
