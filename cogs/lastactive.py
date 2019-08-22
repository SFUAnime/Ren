"""
lastactive (Ren v2) - Tracks when a user was last active.

How to use:
    bot.last_active[server_id][channel_id][author_id] -> Retrieves datetime (UTC) of last message sent by that author in
    that channel in that server.

Last updated by jangarong on August 22nd, 2019.
"""
import asyncio
import json
from datetime import datetime, timedelta


class LastActive:

    """
    json_path : (String) Where the json file is saved/loaded.
    from_json : (Boolean) If true, it will retrieve last active data from json based on path. If false, it will
        retrieve last active data via logs from channels.
    to_json : (Boolean) If true, it will save the json file in the desired path periodically.
    limit : (Integer) Number of messages read in the chat history of each channel. Keep in mind that the larger the
        number, the longer it will take for the bot to set up.

    To change these values, see the setup function down below.
    """
    def __init__(self, bot, json_path='/cogs/lastactive/last_active.json', from_json=False, to_json=True, limit=500):
        self.bot = bot
        self.bot.last_active = {}
        self.json_path = json_path
        self.from_json = from_json
        self.to_json = to_json
        self.limit = limit

        # create loop that goes per day
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.json_loop())

    def _to_json(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.bot.last_active, f)

    def _load_json(self):
        with open(self.json_path, 'r') as f:
            self.bot.last_active = json.load(f)

    # iterate per day to save last active data
    async def json_loop(self):
        while self == self.bot.get_cog("LastActive"):
            if self.lastChecked.day != datetime.now().day:
                self.lastChecked = datetime.now()
                await self.save_data()
            await asyncio.sleep(60)

    async def save_data(self):
        await self._to_json()

    def add_to_db(self, message):

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
                pass

        else:

            # iterate through each channel for messages
            for server in self.bot.servers:

                # add dictionary for server
                for channel in server.channels:
                    if str(channel.type) == 'text':

                        # go through each message and add them to dictionary
                        async for message in self.bot.logs_from(channel, limit=self.limit):
                            self.add_to_db(message)

    # update dictionary with latest post
    async def listener(self, message):
        self.add_to_db(message)


def setup(bot):
    n = LastActive(bot)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
