"""
Cogs Purpose: To be able to hook up any RSS feed(s) to the bot and post it in a channel
Requirements:
    - sudo pip install bs4
    - sudo pip install feedparser
"""
import asyncio
from datetime import datetime
import logging
import aiohttp
import feedparser
from bs4 import BeautifulSoup
import discord
from redbot.core  import checks, Config, commands, data_manager
from redbot.core.bot import Red

KEY_CHANNEL = "post_channel"
KEY_INTERVAL = "check_interval"
KEY_LAST_POST_TIME = "last_post_time"
KEY_FEEDS = "rss_feed_urls"
RSS_IMAGE_URL = ("https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Feed-icon.svg/"
                 "1200px-Feed-icon.svg.png")

def date2epoch(date):
    """Converts a datetime date into epoch for storage in JSON."""
    try:
        epoch = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').timestamp()
    except ValueError:
        epoch = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %Z').timestamp()
        return epoch

    return epoch

def epoch2date(epoch):
    """Converts an epoch time into a datetime date from storage in JSON."""
    date = datetime.fromtimestamp(epoch).strftime('%a, %d %b %Y %I:%M%p')
    return date

def _getLatestPostTime(feedItems):
    publishedTimes = []
    for item in feedItems:
        publishedTimes.append(date2epoch(item['published']))
    if publishedTimes:
        return max(publishedTimes)
    return None #lets be explicit :)

def _isNewItem(latestPostTime, itemPostTime):
    return latestPostTime < itemPostTime

class RSSFeed(commands.Cog):
    """RSS cog"""
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647,
                                      force_registration=True)
        defaultGlobal = {
            "interval": 60
                }
        defaultGuild = {
            "channelId": None,
            "rssFeedUrls": {},

                }
        self.config.register_global(**defaultGlobal)
        self.config.register_guild(**defaultGuild)

        # Initialize logger and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.RSSFeed")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(filename=str(saveFolder) +
                                          "/info.log",
                                          encoding="utf-8",
                                          mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s",
                                  datefmt="[%d/%m/%Y %H:%M:%S]"))
            self.logger.addHandler(handler)

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="rss", pass_context=True, no_pm=True)
    async def _rss(self, ctx):
        """Configuration for the RSS cog"""

    @_rss.command(name="interval", pass_context=True, no_pm=True)
    async def setInterval(self, ctx, minutes: int):
        """Set the interval for RSS to scan for updates.

        Parameters:
        -----------
        minutes: int
            The number of minutes between checks, between 1 and 180 inclusive.
        """
        if minutes < 1 or minutes > 180:
            await ctx.send(":negative_squared_cross_mark: **RSS - Check Interval:** "
                           "The interval must be between 1 and 180 minutes!")
            return

        await self.config.interval.set(minutes*60)

        await ctx.send(":white_check_mark: **RSS - Check Interval:** Interval set to "
                       "**{}** minutes".format(minutes))

        self.logger.info("%s#%s (%s) changed the RSS check interval to %s minutes",
                         ctx.message.author.name,
                         ctx.message.author.discriminator,
                         ctx.message.author.id,
                         minutes)

    @_rss.command(name="channel", pass_context=True, no_pm=True)
    async def setChannel(self, ctx, channel: discord.TextChannel):
        """Set the channel to post new RSS news items.

        Parameters:
        -----------
        channel: discord.Channel
            The channel to post new RSS news items to.
        """
        await self.config.guild(ctx.guild).channelId.set(channel.id)
        await ctx.send(":white_check_mark: **RSS - Channel**: New updates will now "
                       "be posted to {}".format(channel.mention))
        self.logger.info("%s#%s (%s) changed the RSS post channel to %s (%s)",
                         ctx.message.author.name,
                         ctx.message.author.discriminator,
                         ctx.message.author.id,
                         channel.name,
                         channel.id)

    @_rss.command(name="show", pass_context=False, no_pm=True)
    async def showSettings(self, ctx):
        """Show the current RSS configuration."""
        msg = ":information_source: **RSS - Current Settings**:\n```"

        channel = self.bot.get_channel(await self.config.guild(ctx.guild).channelId())
        if not channel:
            await ctx.send("Invalid channel, please set a channel and try again!")
            return
        msg += "Posting Channel: #{}\n".format(channel.name)
        msg += "Check Interval:  {} minutes\n".format(await self.config.interval()/60)
        msg += "```"

        await ctx.send(msg)

    async def getFeed(self, rssUrl, guild):
        """Gets news items from a given RSS URL

        Parameters:
        -----------
        rssUrl: str
            The URL of the RSS feed.
        guild: discord.Guild
            The server where this rss URL comes from
        Returns:
        --------
        news: [feedparser.FeedParserDict]
            A list of news items obtained using the feedparser library.

        Also updates the latest post time for the URL given within the settings
        dict if there is at least one news item.
        """

        try:
            rssDict = await self.config.guild(guild).rssFeedUrls()
            latestPostTime = rssDict[rssUrl][KEY_LAST_POST_TIME]
        except KeyError:
            rssDict[rssUrl][KEY_LAST_POST_TIME] = 0
            latestPostTime = 0

        news = []
        feed = feedparser.parse(rssUrl)

        for item in feed.entries:
            itemPostTime = date2epoch(item['published'])
            if _isNewItem(latestPostTime, itemPostTime):
                news.append(item)

        if not news:
            self.logger.info("No new items from %s", rssUrl)
        else:
            self.logger.info("%s new items from %s", len(news), rssUrl)

        latestPostTime = _getLatestPostTime(feed.entries)
        if latestPostTime:
            rssDict[rssUrl][KEY_LAST_POST_TIME] = latestPostTime

        await self.config.guild(guild).rssFeedUrls.set(rssDict)

        return news

    async def rss(self):
        """RSS background checker.
        Checks for rss updates periodically and posts any new content to the specific
        channel.
        """

        while self == self.bot.get_cog("RSSFeed"):
            self.logger.info("Scanning feed(s) for updates...")
            for guild in self.bot.guilds:
                chID = await self.config.guild(guild).channelId()
                postChannel = self.bot.get_channel(chID)
                updates = []

                if not postChannel:
                    self.logger.error("Can't find channel: bot is not logged in yet.")
                else:
                    rssFeedDict = await self.config.guild(guild).rssFeedUrls()
                    for feedUrl in rssFeedDict.keys():
                        feedUpdates = await self.getFeed(feedUrl, guild)
                        updates += feedUpdates

                # Reversed so updates display from latest to earliest, since they are
                # appended earliest to latest.
                for item in reversed(updates):
                    embed = discord.Embed()
                    embed.colour = discord.Colour.orange()
                    embed.title = item.title
                    embed.url = item.link.replace(" ", "%20")

                    async with aiohttp.ClientSession() as session:
                        async with session.get(item.link.replace(' ', '%20')) as resp:
                            page = await resp.text()

                    soup = BeautifulSoup(page, "html.parser")

                    #ugly, but want a nicer "human readable" date
                    embed.add_field(name="Date Published",
                                    value=epoch2date(date2epoch(item.published)),
                                    inline=False)

                    #Handle empty summary case
                    value = BeautifulSoup(item.summary, "html.parser").get_text()
                    if value:
                        embed.add_field(name="Summary", value=value, inline=False)
                    else:
                        self.logger.info("No summary found. Posting without the summary.")

                    try:
                        embed.set_image(url=soup.find("meta", property="og:image")["content"])
                    except (KeyError, TypeError) as error:
                        self.logger.error("Image URL error: %s", error)

                    embed.set_footer(text="This update is from "
                                     "{}".format(item.title_detail.base),
                                     icon_url=RSS_IMAGE_URL)

                    # Keep this in a try block in case of Discord's explicit filter.
                    try:
                        await postChannel.send(embed=embed)
                    except discord.errors.HTTPException as error:
                        self.logger.error("Could not post to RSS channel!")
                        self.logger.error(error)
                        self.logger.error("Embed: %s", embed.to_dict())

            try:
                await asyncio.sleep(await self.config.interval()) # pylint: disable=no-member
            except asyncio.CancelledError as error:
                self.logger.error("The asyncio sleep was cancelled!")
                self.logger.error(error)
                raise error
