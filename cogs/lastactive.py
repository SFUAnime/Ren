"""
lastactive (Ren v2) - Tracks when a user was last active.

How to use:
    bot.last_active[server_id][channel_id][author_id] -> Retrieves datetime (UTC) of last message sent by that author in
    that channel.
    You can change the parameters of the object in the setup method.

Last updated by jangarong on August 21st, 2019.
"""
import asyncio
import pickle
from datetime import datetime, timedelta


class LastActive:

    """
    pickle_path : (String) Where the pickled file is saved/loaded.
    from_pickle : (Boolean) If true, it will retrieve last active data from pickle based on path. If false, it will
        retrieve last active data via logs from channels.
    to_pickle : (Boolean) If true, it will pickle the last active data and save it in the desired path periodically.
    limit : (Integer) Number of messages read in the chat history of each channel. Keep in mind that the larger the
        number, the longer it will take for the bot to set up.

    To change these values, see the setup function down below.
    """
    def __init__(self, bot, pickle_path='last_active.pkl', from_pickle=False, to_pickle=True, limit=500):
        self.bot = bot
        self.bot.last_active = {}
        self.pickle_path = pickle_path
        self.from_pickle = from_pickle
        self.to_pickle = to_pickle
        self.limit = limit

        # create loop that goes per day
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.pickle_loop())

    def _to_pickle(self):
        with open(self.pickle_path, 'wb') as f:
            pickle.dump(self.bot.last_active, f, pickle.HIGHEST_PROTOCOL)

    def _load_pickle(self):
        with open(self.pickle_path, 'rb') as f:
            self.bot.last_active = pickle.load(f)

    # iterate per day to save last active data
    async def pickle_loop(self):
        while self == self.bot.get_cog("LastActive"):
            if self.lastChecked.day != datetime.now().day:
                self.lastChecked = datetime.now()
                await self.save_data()
            await asyncio.sleep(60)

    async def save_data(self):
        await self._to_pickle()

    def add_to_db(self, message):

        if message.author.id != self.bot.user.id:

            # if the server exists
            if message.server in self.bot.last_active:

                # update timestamp if channel exists
                if message.channel in self.bot.last_active[message.server]:
                    self.bot.last_active[message.server][message.channel][message.author.id] = message.timestamp

                # if the channel did not exist before
                else:
                    self.bot.last_active[message.server][message.channel] = {}
                    self.bot.last_active[message.server][message.channel][message.author.id] = message.timestamp

            # if the server did not exist before
            else:
                self.bot.last_active[message.server] = {}
                self.bot.last_active[message.server][message.channel] = {}
                self.bot.last_active[message.server][message.channel][message.author.id] = message.timestamp

    # limit = number of messages to read in each channel (the larger the number, the longer it'll take to load)
    async def on_ready(self, limit=9999):

        # load pickle
        if self.from_pickle:
            try:
                self._load_pickle()
            except FileNotFoundError:
                pass

        else:

            # iterate through each channel for messages
            for server in self.bot.servers:

                # add dictionary for server
                for channel in server.channels:
                    if str(channel.type) == 'text':

                        # go through each message and add them to dictionary
                        async for message in self.bot.logs_from(channel, limit=limit):
                            self.add_to_db(message)

    # update dictionary with latest post
    async def listener(self, message):
        self.add_to_db(message)


def setup(bot):
    n = LastActive(bot)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
