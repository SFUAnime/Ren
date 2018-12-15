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
from cogs.utils.dataIO import dataIO
from __main__ import send_cmd_help # pylint: disable=no-name-in-module

LOGGER = None
RSS_IMAGE = ("https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Feed-icon.svg/"
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
            print("RSS: Creating folder: {} ...".format(folder))
            os.makedirs(folder)

    files = ("data/rss/config.json", "data/rss/feeds.json")
    for file in files:
        if not os.path.exists(file):
            print("RSS: Creating file: {} ...".format(file))

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
                defaultDict['post_channel'] = "change_me"
                defaultDict['rss_feed_urls'] = ["change_me"]
                defaultDict['check_interval'] = 3600 #default to checking every hour
                dataIO.save_json("data/rss/config.json", defaultDict)

def _getFeed(rssUrl, channel, index=None):

    if channel is None:
        return []

    feeds = dataIO.load_json("data/rss/feeds.json")

    #ensure every rss url has a specified id and most recent post epoch
    try:
        latestPostTime = feeds['feeds'][index]['latest_post_time']
    except IndexError:
        feedDict = {}
        feedDict['id'] = index
        feedDict['latest_post_time'] = 0
        feeds['feeds'].append(feedDict)
        dataIO.save_json("data/rss/feeds.json", feeds)
        feeds = dataIO.load_json("data/rss/feeds.json")
        latestPostTime = feeds['feeds'][index]['latest_post_time']

    news = []
    feed = feedparser.parse(rssUrl)

    for item in feed['items']:
        itemPostTime = date2epoch(item['published'])
        if _isNewItem(latestPostTime, itemPostTime):
            rssItem = {}
            rssItem['title'] = item['title']
            rssItem['link'] = item['link']
            rssItem['published'] = item['published']
            rssItem['summary'] = item['summary']
            rssItem['url'] = rssUrl
            news.append(rssItem)

    if not news:
        LOGGER.info("No new items in feed %s", str(index))
    else:
        LOGGER.info("%s new items in feed %s", len(news), str(index))

    latestPostTime = _getLatestPostTime(feed['items'])
    if latestPostTime:
        feeds['feeds'][index]['latest_post_time'] = latestPostTime
    dataIO.save_json("data/rss/feeds.json", feeds)

    # Heartbeat
    dataIO.save_json("data/rss/timestamp.json", "{}")

    return news

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
        self.settings = dataIO.load_json("data/rss/config.json")
        self.bot = bot
        self.rssFeedUrls = self.settings['rss_feed_urls']
        self.checkInterval = self.settings['check_interval']
        self.channelId = self.settings['post_channel']

    @commands.group(name="rss", pass_context=True, no_pm=True)
    async def _rss(self, ctx):
        """Utilities for the RSS cog"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_rss.command(pass_context=True, no_pm=True)
    async def setinterval(self, ctx):
        """Set the interval for rss to scan for updates"""

    async def rss(self): # pylint: disable=too-many-locals
        """RSS background checker.
        Checks for rss updates periodically and posts any new content to the specific
        channel.
        """

        while self == self.bot.get_cog("RSSFeed"):
            LOGGER.info("Scanning feed(s) for updates...")

            postChannel = self.bot.get_channel(self.channelId)
            updates = []
            idx = 0

            if not postChannel:
                LOGGER.error("Can't find channel: bot is not logged in yet.")

            for feedUrl in self.rssFeedUrls:
                feedUpdates = _getFeed(feedUrl, postChannel, index=idx)
                updates += feedUpdates
                idx += 1

            # Reversed so updates display from latest to earliest, since they are
            # appended earliest to latest.
            for item in reversed(updates):
                embed = discord.Embed()
                embed.colour = discord.Colour.orange()
                embed.title = item['title']
                embed.url = item['link']

                async with aiohttp.ClientSession() as session:
                    async with session.get(item['link'].replace(' ', '%20')) as resp:
                        page = await resp.text()

                soup = BeautifulSoup(page, "html.parser")
                try:
                    imageUrl = soup.find("meta", property="og:image")['content']
                    embed.set_image(url=imageUrl)
                except (KeyError, TypeError):
                    pass

                #ugly, but want a nicer "human readable" date
                formattedDate = epoch2date(date2epoch(item['published']))
                embed.add_field(name="Date Published", value=formattedDate, inline=False)

                html2text = BeautifulSoup(item['summary'], "html.parser").get_text()
                embed.add_field(name="Summary", value=html2text, inline=False)

                footerText = "This update is from {}".format(item['url'])
                rssImage = RSS_IMAGE
                embed.set_footer(text=footerText, icon_url=rssImage)

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
