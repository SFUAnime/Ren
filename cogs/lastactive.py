"""
lastactive (Ren v2) - Tracks when a user was last active.

How to use:
    bot.last_active[server_id][channel_id][author_id] -> Retrieves datetime (UTC) of last message sent by that author in
    that channel in that server.

Last updated by jangarong on August 22nd, 2019.
"""
import os
import asyncio
import json
from datetime import datetime, timedelta


class LastActive:

    """
    from_json : (Boolean) If true, it will retrieve last active data from json based on path. If false, it will
        retrieve last active data via logs from channels.
    to_json : (Boolean) If true, it will save the json file in the desired path periodically.
    limit : (Integer) Number of messages read in the chat history of each channel. Keep in mind that the larger the
        number, the longer it will take for the bot to set up.

    To change these values, see the setup function down below.
    """
    def __init__(self, bot, from_json=False, to_json=True, limit=500):
        self.bot = bot
        self.bot.last_active = {}
        self.from_json = from_json
        self.to_json = to_json
        self.limit = limit

        # working directory = cogs
        self.json_path = os.path.abspath(os.path.dirname(__file__))[:-len('/cogs')] + '/data/lastactive/' \
                                                                                      'last_active.json'

        # create loop that goes every 15 minutes
        self.lastChecked = datetime.now() - timedelta(minutes=15)
        self.bgTask = self.bot.loop.create_task(self.json_loop())

    def create_folder(self):
        folder_name = self.json_path[:-len('last_active.json')]
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

    def _to_json(self):
        self.create_folder()
        with open(self.json_path, 'w') as f:
            json.dump(self.bot.last_active, f)

    def _load_json(self):
        with open(self.json_path, 'r') as f:
            self.bot.last_active = json.load(f)

    # iterate per day to save last active data
    async def json_loop(self):
        while self == self.bot.get_cog("LastActive"):
            if (self.lastChecked + timedelta(minutes=15)).minute == datetime.now().minute:
                self.lastChecked = datetime.now()
                self._load_json()
            await asyncio.sleep(60)

    def add_to_dict(self, message):

        if message.author.id != self.bot.user.id:

            # if the server exists
            if message.server.id in self.bot.last_active:

                # update timestamp if channel exists
                if message.channel.id in self.bot.last_active[message.server.id]:
                    self.bot.last_active[message.server.id][message.channel.id][message.author.id] = message.timestamp

                # if the channel did not exist before
                else:
                    self.bot.last_active[message.server.id][message.channel.id] = {}
                    self.bot.last_active[message.server.id][message.channel.id][message.author.id] = message.timestamp

            # if the server did not exist before
            else:
                self.bot.last_active[message.server.id] = {}
                self.bot.last_active[message.server.id][message.channel.id] = {}
                self.bot.last_active[message.server.id][message.channel.id][message.author.id] = message.timestamp

    async def on_ready(self):

        # load json
        if self.from_json:
            try:
                self._load_json()
            except FileNotFoundError:
                self.create_folder()

        else:

            # iterate through each channel for messages
            for server in self.bot.servers:

                # add dictionary for server
                for channel in server.channels:
                    if str(channel.type) == 'text':

                        # go through each message and add them to dictionary
                        async for message in self.bot.logs_from(channel, limit=self.limit):
                            self.add_to_dict(message)

    # update dictionary with latest post
    async def listener(self, message):
        self.add_to_dict(message)


def setup(bot):
    n = LastActive(bot, to_json=True)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
