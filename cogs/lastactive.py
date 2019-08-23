"""
lastactive (Ren v2) - Tracks when a user was last active.

How to use:
    bot.last_active[server_id][channel_id][author_id] -> Retrieves datetime (UTC) of last message
    sent by that author in that channel in that server.

Last updated by jangarong on August 22nd, 2019.
"""
import os
import asyncio
from jsondt import json
from datetime import datetime, timedelta


class LastActive:

    def __init__(self, bot, fromJson=False, toJson=True, limit=500):
        """
        fromJson : (Boolean) If true, it will retrieve last active data from json based on path. If
            false, it will retrieve last active data via logs from channels.
        toJson : (Boolean) If true, it will save the json file in the desired path periodically.
        limit : (Integer) Number of messages read in the chat history of each channel. Keep in mind
            that the larger the number, the longer it will take for the bot to set up.

        To change these values, see the setup function down below.
        """
        self.bot = bot
        self.bot.lastActive = {}
        self.fromJson = fromJson
        self.toJson = toJson
        self.limit = limit

        # working directory = cogs
        self.jsonPath = os.path.abspath(os.path.dirname(__file__))[:-len('/cogs')] + \
                        '/data/lastactive/last_active.json'

        # create loop that goes every minute
        self.bgTask = self.bot.loop.create_task(self.jsonLoop())

    def createFolder(self):
        """Creates a folder in case if one did not exist already."""
        folderName = self.jsonPath[:-len('last_active.json')]
        if not os.path.exists(folderName):
            os.makedirs(folderName)

    def dumpJson(self):
        """Saves dictionary into json."""
        self.createFolder()
        with open(self.jsonPath, 'w') as file:
            json.dump(self.bot.lastActive, file)

    def loadJson(self):
        """Loads dictionary into json."""
        with open(self.jsonPath, 'r') as file:
            self.bot.lastActive = json.load(file)

    async def jsonLoop(self):
        """Saves dictionary into json file every minute."""
        while self == self.bot.get_cog("LastActive"):
            self.dumpJson()
            await asyncio.sleep(60)

    def addToDict(self, message):
        """Retrieves metadata from the message and places it accordingly in the dictionary."""
        if message.author.id != self.bot.user.id:

            # if the server exists
            if message.server.id in self.bot.lastActive:

                # update timestamp if channel exists
                if message.channel.id in self.bot.lastActive[message.server.id]:
                    self.bot.lastActive[message.server.id][message.channel.id][message.author.id] \
                        = message.timestamp

                # if the channel did not exist before
                else:
                    self.bot.lastActive[message.server.id][message.channel.id] = {}
                    self.bot.lastActive[message.server.id][message.channel.id][message.author.id] \
                        = message.timestamp

            # if the server did not exist before
            else:
                self.bot.lastActive[message.server.id] = {}
                self.bot.lastActive[message.server.id][message.channel.id] = {}
                self.bot.lastActive[message.server.id][message.channel.id][message.author.id] = \
                    message.timestamp

    async def on_ready(self):
        """Depending on the parameters given in __init__, it will either try
        to read from an existing json file, and use that as a dictionary, or read
        n messages from every text channel."""
        # load json
        if self.fromJson:
            try:
                self.loadJson()
            except FileNotFoundError:
                self.createFolder()

        else:

            # iterate through each channel for messages
            for server in self.bot.servers:

                # add dictionary for server
                for channel in server.channels:
                    if str(channel.type) == 'text':

                        # go through each message and add them to dictionary
                        async for message in self.bot.logs_from(channel, limit=self.limit):
                            self.addToDict(message)

    # update dictionary with latest post
    async def listener(self, message):
        """For every message, add to dictionary."""
        self.addToDict(message)


def setup(bot):
    n = LastActive(bot, toJson=True)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
