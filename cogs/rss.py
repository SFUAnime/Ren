import discord
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
# DEBUG
import os
os.environ['PYTHONASYNCIODEBUG'] = '1'
# DEBUG
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from urllib import request #TODO: use aiohttp instead
from bs4 import BeautifulSoup

"""
Cogs Purpose: To be able to hook up any RSS feed(s) to the bot and post it in a channel
Requirements: 
    - sudo pip install bs4
    - sudo pip install feedparser
"""

def date2epoch(date):
    try:
        epoch = datetime.strptime(date,'%a, %d %b %Y %H:%M:%S %z').timestamp()
    except ValueError:
        epoch = datetime.strptime(date,'%a, %d %b %Y %H:%M:%S %Z').timestamp()
        return epoch
        
    return epoch
    
def epoch2date(epoch):
    date = datetime.fromtimestamp(epoch).strftime('%a, %d %b %Y %I:%M%p')
    return date
    
def config_setup():
    print("RSS: insert the channel id of where the bot should post:")
    config_channel = None
    while config_channel is None:
        config_channel = str(input("> "))
        
    print("RSS: insert the rss url(s) for the bot to monitor:")
    print("RSS: insert d to finish adding rss urls")
    config_feeds = []
    while True:
        latest = input("> ")
        if latest == "d":
            break
        config_feeds.append(str(latest))
        
    dict = {}
    dict["channel"] = config_channel
    dict["feeds"] = config_feeds
    return dict
    
def check_filesystem():

    folders = ["data/rss"]
    for folder in folders:
        if not os.path.exists(folder):
            print("RSS: Creating folder: {} ...".format(folder))
            os.makedirs(folder)
            
    files = ["data/rss/config.json", "data/rss/feeds.json"]
    for file in files:
        if not os.path.exists(file):
            if "feeds" in file:
                #build a default feeds.json
                dict = {}
                default_feed = {}
                default_feed['id'] = 0
                default_feed['latest_post_time'] = 0
                dict['feeds'] = []
                dict['feeds'].append(default_feed)
                dataIO.save_json("data/rss/feeds.json",dict)
            elif "config" in file:
                #build a default config.json
                dict = {}
                config = config_setup()
                dict['post_channel'] = config["channel"]
                dict['rss_feed_urls'] = config["feeds"]
                dict['check_interval'] = 3600 #default to checking every hour
                dataIO.save_json("data/rss/config.json",dict)
                
            print("RSS: Creating file: {} ...".format(file))
            
class RSSFeed(object):
    def __init__(self, bot):
        self.settings = dataIO.load_json("data/rss/config.json")
        self.bot = bot
        self.rss_feed_urls = self.settings['rss_feed_urls']
        self.check_interval = self.settings['check_interval']
        self.channel_id = self.settings['post_channel']
        
    def _is_new_item(self,latest_post_time, item_post_time):
        return latest_post_time < item_post_time
           
    def _get_latest_post_time(self, feed_items):
        published_times = []
        for item in feed_items:
            published_times.append(date2epoch(item['published']))
        if published_times:
            return max(published_times)
        else:
            return None #lets be explicit :)
            
    @commands.group(name="rss", pass_context=True, no_pm=True)
    async def _rss(self, ctx):
        """Utilities for the RSS cog"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            
    @_rss.command(pass_context=True, no_pm=True)
    async def setinterval(self,ctx):
        """Set the interval for rss to scan for updates"""
        pass
        
    def _get_feed(self, rss_url, channel, index=None): 
        
        if channel is None:
            return []
        
        feeds = dataIO.load_json("data/rss/feeds.json")
        
        #ensure every rss url has a specified id and most recent post epoch
        try:
            latest_post_time = feeds['feeds'][index]['latest_post_time']
        except IndexError:
            dict = {}
            dict['id'] = index
            dict['latest_post_time'] = 0
            feeds['feeds'].append(dict)
            dataIO.save_json("data/rss/feeds.json",feeds)
            feeds = dataIO.load_json("data/rss/feeds.json")
            latest_post_time = feeds['feeds'][index]['latest_post_time']
        
        news = []
        feed = feedparser.parse(rss_url)
        
        for item in feed['items']:
            item_post_time = date2epoch(item['published'])
            if self._is_new_item(latest_post_time, item_post_time):
                dict = {}
                dict['title'] = item['title']
                dict['link'] = item['link']
                dict['published'] = item['published']
                dict['summary'] = item['summary']
                dict['url'] = rss_url
                news.append(dict)
                
        if len(news) == 0:
            print("RSS: no new items in feed {}".format(str(index)))
        else:
            print("RSS: {} new items in feed {}".format(len(news), str(index)))
        
        latest_post_time = self._get_latest_post_time(feed['items'])
        if latest_post_time is not None:
            feeds['feeds'][index]['latest_post_time'] = latest_post_time
        dataIO.save_json("data/rss/feeds.json", feeds)
        
        return news
               
    async def _rss(self):
        """ Checks for rss updates periodically and posts any new content to the specific channel"""
        
        await self.bot.wait_until_ready()
        
        while self == self.bot.get_cog("RSSFeed"):
            print("------------------------------------")
            print("RSS: scanning feed(s) for updates...")
            print("------------------------------------")
            
            post_channel = self.bot.get_channel(self.channel_id)
            updates = []
            idx = 0
            
            if post_channel is None:
                print("RSS: Can't find channel, Bot is not yet logged in.")
            
            for feed_url in self.rss_feed_urls:
                feed_updates = self._get_feed(feed_url, post_channel, index=idx)
                updates += feed_updates
                idx += 1
            
            #reversed so updates display from latest to earliest, since they are appended earliest to latest
            for item in reversed(updates): 
                embed = discord.Embed()
                embed.colour = discord.Colour.orange()
                embed.title = item['title']
                embed.url = item['link']
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(item['link']) as resp:
                        page = await resp.text()
                
                soup = BeautifulSoup(page, "html.parser")
                try:
                    image_url = soup.find("meta", property="og:image")['content']
                    embed.set_image(url=image_url)
                except (KeyError, TypeError):
                    pass
                
                #ugly, but want a nicer "human readable" date
                formatted_date = epoch2date(date2epoch(item['published']))
                embed.add_field(name="Date Published", value=formatted_date, inline=False)
                
                html2text = BeautifulSoup(item['summary'], "html.parser").get_text()
                embed.add_field(name="Summary", value=html2text, inline=False)
                
                footer_text = "This update is from {}".format(item['url'])
                rss_image = "https://upload.wikimedia.org/wikipedia/en/thumb/4/43/Feed-icon.svg/1200px-Feed-icon.svg.png"
                embed.set_footer(text=footer_text, icon_url=rss_image)
                
                await self.bot.send_message(post_channel, embed=embed)
                
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError as e:              
                print("borked")                        
                raise e
            
def setup(bot):
    check_filesystem()
    rss_obj = RSSFeed(bot)
    bot.add_cog(rss_obj)
    bot.loop.create_task(rss_obj._rss())
