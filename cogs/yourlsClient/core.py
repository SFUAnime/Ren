import asyncio
import logging
import os

import discord

from redbot.core import Config, data_manager
from redbot.core.bot import Red

from .api import YOURLSClient
from .constants import BASE_GUILD, KEY_API, KEY_SIGNATURE
from .exceptions import YOURLSNotConfigured


class Core:
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)
        self.loop = asyncio.get_running_loop()

        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.YOURLS")
        if not self.logger.handlers:
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%Y/%m/%d %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    async def fetchYourlsClient(self, guild: discord.Guild):
        """Create the YOURLS client.

        Parameters
        ----------
        guild: discord.Guild
            The guild to look up the YOURLS API configuration for.

        Returns
        -------
        yourls.YOURLSClient
            The YOURLS client, which you can use to interact with your YOURLS instance.

        Raises
        ------
        YOURLSNotConfigured
            Unable to create the YOURLS client because of missing information.
        """
        api = await self.config.guild(guild).get_attr(KEY_API)()
        sig = await self.config.guild(guild).get_attr(KEY_SIGNATURE)()
        if not (api and sig):
            raise YOURLSNotConfigured("Please configure the YOURLS API first.")
        return YOURLSClient(api, signature=sig)
