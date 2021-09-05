"""GoodSmileCompany cog
Post updates from GSC's site.
"""

import asyncio
import os
import aiohttp
from bs4 import BeautifulSoup
import discord
import logging

from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

KEY_POST_CHANNEL = "postChannel"
KEY_URLS = "urls"
DEFAULT_GUILD = {KEY_POST_CHANNEL: None, KEY_URLS: {}}

URL = "https://www.goodsmile.info/en/posts/category/information/date/"
# XXX Use another library to strip URL to root
BASE_URL = "https://www.goodsmile.info"
SLEEP_TIME = 3600  # In seconds


class GoodSmileInfo(commands.Cog):
    """Fetch Good Smile Company info"""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.GoodSmileInfo")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.DEBUG)
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

        self.bgTask = self.bot.loop.create_task(self.bgLoop())

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.bgTask.cancel()

    def cog_unload(self):
        self.logger.debug("Cog unloaded, cancelling background task")
        self.__unload()

    @commands.group(name="goodsmileinfo")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def gscInfo(self, ctx: Context):
        """Good Smile Company (GSC) information poster."""

    @gscInfo.command(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setChannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to post GSC updates.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            A text channel to post updates to. Pass nothing in to disable.
        """
        if channel:
            await self.config.guild(ctx.message.guild).get_attr(KEY_POST_CHANNEL).set(channel.id)
            self.logger.info(
                "%s#%s (%s) set the post channel to %s",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
                channel.name,
            )
            await ctx.send(
                ":white_check_mark: **GSC - Channel**: **{}** has been set "
                "as the update channel!".format(channel.name)
            )
        else:
            await self.config.guild(ctx.message.guild).get_attr(KEY_POST_CHANNEL).set(None)
            await ctx.send(":white_check_mark: **GSC - Channel**: GSC updates are now disabled.")

    async def bgLoop(self):
        while self == self.bot.get_cog("GoodSmileInfo"):
            self.logger.debug("Checking GSC info")
            embeds = await self.checkGscInfo()
            await self.maybePostInfoToGuilds(embeds)
            await asyncio.sleep(SLEEP_TIME)

    async def checkGscInfo(self):
        """Check GSC site and generate embeds

        Returns
        -------
        listOfEmbeds: [discord.Embed]
            A list of embeds for all fetched news articles
        """
        self.logger.debug("Fetching info from GSC")
        listOfEmbeds = []
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as resp:
                page = await resp.text()

        soup = BeautifulSoup(page, "html.parser")
        news = soup("div", class_="newsItem")

        for update in news:
            # Parse info and create embeds
            date = update(class_="newsDate")[0].text.strip()
            category = update(class_="newsCat")[0].text.strip()
            title = update(class_="newsTtlBd")[0].text.strip()
            url = update.a["href"]

            embed = discord.Embed(title=title)
            embed.add_field(name="Date", value=date)
            embed.add_field(name="Category", value=category)
            embed.colour = discord.Colour.orange()
            embed.url = BASE_URL + url.replace(" ", "%20")
            embed.set_footer(text="Good Smile Company News")

            # Fetch the actual page to get info on the post
            async with aiohttp.ClientSession() as session:
                async with session.get(BASE_URL + url) as resp:
                    page = await resp.text()
            detailsSoup = BeautifulSoup(page, "html.parser")

            summary = detailsSoup(class_="itemOut")[0](class_="clearfix")[0].text
            if len(summary) > 1024:
                summary = summary[0:1018] + "..."
            embed.description = summary

            listOfEmbeds.append(embed)
        self.logger.debug("Fetched %s news entries", len(listOfEmbeds))
        return listOfEmbeds

    async def maybePostInfoToGuilds(self, listOfEmbeds: [discord.Embed]):
        """Post GSC info to each guild.

        This will check the url of each embed. If it has already been posted once, this
        method will skip them and not post.

        Parameters
        ----------
        listOfEmbeds: [discord.Embed]
            A list of embeds, generated using checkGscInfo
        """
        for guild in self.bot.guilds:
            postChannel = await self.config.guild(guild).get_attr(KEY_POST_CHANNEL)()
            if not postChannel:
                self.logger.debug("No post channel configured, skipping")
                continue

            channel = self.bot.get_channel(postChannel)
            if not channel:
                self.logger.debug(
                    "Cannot find channel ID %s, does the channel still exist?", postChannel
                )
                continue

            for embed in listOfEmbeds:
                if embed.url in await self.config.guild(guild).get_attr(KEY_URLS)():
                    self.logger.debug("Sent before, skipping")
                    continue
                else:
                    async with self.config.guild(guild).get_attr(KEY_URLS)() as urls:
                        urls[embed.url] = True
                    self.logger.debug("Not sent before, will send")

                try:
                    await channel.send(embed=embed)
                except (discord.Forbidden, discord.HTTPException) as errorMsg:
                    self.logger.error(
                        "Could not send message, not enough permissions",
                        exc_info=True,
                    )
                    self.logger.error(errorMsg)
                else:
                    self.logger.debug("Post successful")
