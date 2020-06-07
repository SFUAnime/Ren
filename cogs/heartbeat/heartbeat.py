import discord
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
import asyncio #Used for task loop.
import os #Used to create folder at first load.
from datetime import datetime

saveFolder = "data/lui-cogs/heartbeat/" #Path to save folder.

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(saveFolder):
        print("Creating " + saveFolder + " folder...")
        os.makedirs(saveFolder)

class Heartbeat:
    """Heartbeat for uptime checks, to be used with a web server backend."""

    def __init__(self, bot):
        self.bot = bot
        self.time_interval = 295
        checkFolder()

    async def _loop(self):
        print("Heartbeat is now running, and is running at "+str(self.time_interval)+" second intervals")
        while self == self.bot.get_cog("Heartbeat"):

            #Heartbeat
            dataIO.save_json("data/lui-cogs/heartbeat/timestamp.json","{}")
            try:
                await asyncio.sleep(self.time_interval)
            except asyncio.CancelledError as e:
                print("Error in sleeping")
                raise e

    @commands.command(name="heartbeat", pass_context=False, no_pm=True)
    async def _check(self):
        await self.bot.say("**In-house** is responding.")

def setup(bot):
    #check_filesystem()
    hb_object = Heartbeat(bot)
    bot.add_cog(hb_object)
    bot.loop.create_task(hb_object._loop())
