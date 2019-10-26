"""
lastactive (Ren v2) - Tracks when a user was last active.

How to use:
    bot.last_active[server_id][channel_id][author_id] -> Retrieves datetime (UTC) of last message
    sent by that author in that channel in that server.

Last updated by jangarong on August 22nd, 2019.
"""
import os
import asyncio
import jsondt as json


class LastActive:
    """Tracks when a user was last active in a channel via dictionary."""

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

        # create loop that goes every minute
        self.bgTask = self.bot.loop.create_task(self.jsonLoop())

    def dumpJson(self):
        """Saves dictionary into json."""
        createFolder()
        with open('data/lastactive/last_active.json', 'w') as file:
            json.dump(self.bot.lastActive, file)

    def loadJson(self):
        """Loads dictionary into json."""
        with open('data/lastactive/last_active.json', 'r') as file:
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

    # update dictionary with latest post
    async def onMessage(self, message):
        """For every message, add to dictionary."""
        self.addToDict(message)

    async def onReady(self):
        """Depending on the parameters given in __init__, it will either try
        to read from an existing json file, and use that as a dictionary, or read
        n messages from every text channel."""
        # load json
        if self.fromJson:
            try:
                self.loadJson()
            except FileNotFoundError:
                createFolder()

        else:

            # iterate through each channel for messages
            for server in self.bot.servers:

                # add dictionary for server
                for channel in server.channels:
                    if str(channel.type) == 'text':

                        # go through each message and add them to dictionary
                        async for message in self.bot.logs_from(channel, limit=self.limit):
                            self.addToDict(message)


def createFolder():
    """Creates a folder in case if one did not exist already."""
    folderName = 'data/lastactive/'
    if not os.path.exists(folderName):
        os.makedirs(folderName)


def setup(bot):
    """Add cog to bot."""
    cog = LastActive(bot, toJson=True)
    bot.add_listener(cog.onMessage, "on_message")
    bot.add_listener(cog.onReady, "on_ready")
    bot.add_cog(cog)
