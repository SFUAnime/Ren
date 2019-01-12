"""
Cogs Purpose: To be able to hook up any RSS feed(s) to the bot and post it in a channel
Requirements:
    - sudo pip install bs4
    - sudo pip install feedparser
"""
import asyncio
from datetime import datetime
import logging
import os

import aiohttp
import discord
from discord.ext import commands
import feedparser
from bs4 import BeautifulSoup
from cogs.utils import checks, config
from cogs.utils.dataIO import dataIO

LOGGER = None
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

def checkFilesystem():
    """Check if the folders/files are created."""
    folders = ("data/rss")
    for folder in folders:
        if not os.path.exists(folder):
            LOGGER.info("Creating folder: %s ...", folder)
            os.makedirs(folder)

    files = ("data/rss/config.json", "data/rss/feeds.json")
    for file in files:
        if not os.path.exists(file):
            LOGGER.info("Creating file: %s...", file)

            if "feeds" in file:
                #build a default feeds.json
                defaultDict = {}
                defaultFeedItem = {}
                defaultFeedItem['id'] = 0
                defaultFeedItem['latest_post_time'] = 0
                defaultDict['feeds'] = []
                defaultDict['feeds'].append(defaultFeedItem)
                dataIO.save_json("data/rss/feeds.json", defaultDict)
            elif "config" in file:
                #build a default config.json
                defaultDict = {}
                defaultDict[KEY_CHANNEL] = "change_me"
                defaultDict[KEY_FEEDS] = {}
                defaultDict[KEY_INTERVAL] = 3600 #default to checking every hour
                dataIO.save_json("data/rss/config.json", defaultDict)

def _getLatestPostTime(feedItems):
    publishedTimes = []
    for item in feedItems:
        publishedTimes.append(date2epoch(item['published']))
    if publishedTimes:
        return max(publishedTimes)
    return None #lets be explicit :)

def _isNewItem(latestPostTime, itemPostTime):
    return latestPostTime < itemPostTime

class RSSFeed():
    """RSS cog"""
    def __init__(self, bot):
        self.config = config.Config("config.json",
                                    cogname="rss")
        self.settings = dataIO.load_json("data/rss/config.json")
        self.bot = bot
        self.rssFeedUrls = self.config.get(KEY_FEEDS)
        self.checkInterval = self.config.get(KEY_INTERVAL)
        self.channelId = self.config.get(KEY_CHANNEL)

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="rss", pass_context=True, no_pm=True)
    async def _rss(self, ctx):
        """Configuration for the RSS cog"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_rss.command(name="interval", pass_context=True, no_pm=True)
    async def setInterval(self, ctx, minutes: int):
        """Set the interval for RSS to scan for updates.

        Parameters:
        -----------
        minutes: int
            The number of minutes between checks, between 1 and 180 inclusive.
        """
        if minutes < 1 or minutes > 180:
            await self.bot.say(":negative_squared_cross_mark: **RSS - Check Interval:** "
                               "The interval must be between 1 and 180 minutes!")
            return

        self.checkInterval = minutes * 60
        await self.config.put(KEY_INTERVAL, self.checkInterval)

        await self.bot.say(":white_check_mark: **RSS - Check Interval:** Interval set to "
                           "**{}** minutes".format(minutes))

        LOGGER.info("%s#%s (%s) changed the RSS check interval to %s minutes",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id,
                    minutes)

    @_rss.command(name="channel", pass_context=True, no_pm=True)
    async def setChannel(self, ctx, channel: discord.Channel):
        """Set the channel to post new RSS news items.

        Parameters:
        -----------
        channel: discord.Channel
            The channel to post new RSS news items to.
        """
        self.channelId = channel.id
        await self.bot.say(":white_check_mark: **RSS - Channel**: New updates will now "
                           "be posted to {}".format(channel.mention))
        LOGGER.info("%s#%s (%s) changed the RSS post channel to %s (%s)",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id,
                    channel.name,
                    channel.id)

    @_rss.command(name="show", pass_context=False, no_pm=True)
    async def showSettings(self):
        """Show the current RSS configuration."""
        msg = ":information_source: **RSS - Current Settings**:\n```"

        channel = self.bot.get_channel(self.channelId)
        if not channel:
            await self.bot.say("Invalid channel, please set a channel and try again!")
            return
        msg += "Posting Channel: #{}\n".format(channel.name)
        msg += "Check Interval:  {} minutes\n".format(self.checkInterval/60)
        msg += "```"

        await self.bot.say(msg)

    async def getFeed(self, rssUrl):
        """Gets news items from a given RSS URL

        Parameters:
        -----------
        rssUrl: str
            The URL of the RSS feed.

        Returns:
        --------
        news: [feedparser.FeedParserDict]
            A list of news items obtained using the feedparser library.

        Also updates the latest post time for the URL given within the settings
        dict if there is at least one news item.
        """

        try:
            latestPostTime = self.rssFeedUrls[rssUrl][KEY_LAST_POST_TIME]
        except KeyError:
            self.rssFeedUrls[rssUrl][KEY_LAST_POST_TIME] = 0
            latestPostTime = 0

        news = []
        feed = feedparser.parse(rssUrl)

        for item in feed.entries:
            itemPostTime = date2epoch(item['published'])
            if _isNewItem(latestPostTime, itemPostTime):
                news.append(item)

        if not news:
            LOGGER.info("No new items from %s", rssUrl)
        else:
            LOGGER.info("%s new items from %s", len(news), rssUrl)

        latestPostTime = _getLatestPostTime(feed.entries)
        if latestPostTime:
            self.rssFeedUrls[rssUrl][KEY_LAST_POST_TIME] = latestPostTime

        await self.config.put(KEY_FEEDS, self.rssFeedUrls)

        # Heartbeat
        dataIO.save_json("data/rss/timestamp.json", "{}")

        return news

    async def rss(self):
        """RSS background checker.
        Checks for rss updates periodically and posts any new content to the specific
        channel.
        """

        while self == self.bot.get_cog("RSSFeed"):
            LOGGER.info("Scanning feed(s) for updates...")

            postChannel = self.bot.get_channel(self.channelId)
            updates = []

            if not postChannel:
                LOGGER.error("Can't find channel: bot is not logged in yet.")
            else:
                for feedUrl in self.rssFeedUrls.keys():
                    feedUpdates = await self.getFeed(feedUrl)
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

                embed.add_field(name="Summary",
                                value=BeautifulSoup(item.summary, "html.parser").get_text(),
                                inline=False)

                try:
                    embed.set_image(url=soup.find("meta", property="og:image")["content"])
                except (KeyError, TypeError) as error:
                    LOGGER.error("Image URL error: %s", error)

                embed.set_footer(text="This update is from "
                                 "{}".format(item.title_detail.base),
                                 icon_url=RSS_IMAGE_URL)

                # Keep this in a try block in case of Discord's explicit filter.
                try:
                    await self.bot.send_message(postChannel, embed=embed)
                except discord.errors.HTTPException as error:
                    LOGGER.error("Could not post to RSS channel!")
                    LOGGER.error(error)

            try:
                await asyncio.sleep(self.checkInterval)
            except asyncio.CancelledError as error:
                LOGGER.error("The asyncio sleep was cancelled!")
                LOGGER.error(error)
                raise error

def setup(bot):
    """Add the cog to the bot."""
    #checkFilesystem()
    global LOGGER # pylint: disable=global-statement
    LOGGER = logging.getLogger("red.RSSFeed")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/rss/info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    rssCog = RSSFeed(bot)
    bot.add_cog(rssCog)
    bot.loop.create_task(rssCog.rss())
