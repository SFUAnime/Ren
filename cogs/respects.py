"""Respects cog
A replica of +f seen in another bot, except smarter..
"""
import copy
from datetime import datetime, timedelta
from threading import Lock
from random import choice
import discord
from discord.ext import commands

KEY_USERS = "users"
KEY_TIME = "time"
KEY_MSG = "msg"
HEARTS = [":green_heart:", ":heart:", ":black_heart:", ":yellow_heart:",
          ":purple_heart:", ":blue_heart:"]
DEFAULT_CH_DICT = {KEY_MSG : None, KEY_TIME : None, KEY_USERS : []}
TIME_BETWEEN = timedelta(seconds=30) # Time between paid respects.
MESSAGES = 20 # The number of messages in between
TEXT_RESPECTS = "paid their respects"

class Respects:
    """Pay your respects."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot
        self.plusFLock = Lock()
        self.settingsLock = Lock()
        self.settings = {}

    @commands.command(name="f", pass_context=True, no_pm=True)
    async def plusF(self, ctx):
        """Pay your respects."""
        with self.plusFLock:
            if not await self.checkLastRespect(ctx):
                # New respects to be paid
                await self.payRespects(ctx)
            elif not self.checkIfUserPaidRespect(ctx):
                # Respects exists, user has not paid their respects yet.
                await self.payRespects(ctx)
            else:
                # Respects already paid by user!
                pass
            await self.bot.delete_message(ctx.message)

    async def checkLastRespect(self, ctx):
        """Check to see if respects have been paid already.

        This method only checks the time portion and previous messages.

        This method returns False if:
        - No respects have been paid in this channel before, or
        - The time exceeds the threshold AND the last respect in the channel was more
          than a certain number of messages.

        Otherwise, this method returns True.
        """
        with self.settingsLock:
            sid = ctx.message.server.id
            cid = ctx.message.channel.id

            if sid not in self.settings.keys():
                self.settings[sid] = {}
                self.settings[sid][cid] = copy.deepcopy(DEFAULT_CH_DICT)
                return False

            if cid not in self.settings[sid].keys():
                self.settings[sid][cid] = copy.deepcopy(DEFAULT_CH_DICT)
                return False

            prevMsgs = []
            async for msg in self.bot.logs_from(ctx.message.channel,
                                                limit=MESSAGES,
                                                before=ctx.message):
                prevMsgs.append(msg.id)

            exceedMessages = self.settings[sid][cid][KEY_MSG].id not in prevMsgs
            exceedTime = datetime.now() - self.settings[sid][cid][KEY_TIME] > TIME_BETWEEN

            if exceedMessages and exceedTime:
                self.settings[sid][cid] = copy.deepcopy(DEFAULT_CH_DICT)
                return False

            return True

    def checkIfUserPaidRespect(self, ctx):
        """Check to see if the user has already paid their respects.

        This assumes that checkLastRespectTime returned True.
        """
        with self.settingsLock:
            sid = ctx.message.server.id
            cid = ctx.message.channel.id
            if ctx.message.author.id in self.settings[sid][cid][KEY_USERS]:
                return True
            return False

    async def payRespects(self, ctx):
        """Pay respects.

        This assumes that checkLastRespectTime has been invoked.

        """
        with self.settingsLock:
            sid = ctx.message.server.id
            cid = ctx.message.channel.id
            uid = ctx.message.author.id

            self.settings[sid][cid][KEY_USERS].append(uid)

            self.settings[sid][cid][KEY_TIME] = datetime.now()
            if self.settings[sid][cid][KEY_MSG]:
                try:
                    await self.bot.delete_message(self.settings[sid][cid][KEY_MSG])
                except: # pylint: disable=bare-except
                    pass
                finally:
                    self.settings[sid][cid][KEY_MSG] = None

            if len(self.settings[sid][cid][KEY_USERS]) == 1:
                message = "**{}** has paid their respects {}".format(ctx.message.author.name,
                                                                     choice(HEARTS))
            elif len(self.settings[sid][cid][KEY_USERS]) == 2: # 2 users, no comma.
                user1 = ctx.message.author
                uid2 = self.settings[sid][cid][KEY_USERS][0]
                user2 = discord.utils.get(ctx.message.server.members, id=uid2)
                users = "**{} and {}**".format(user1.name, user2.name)
                message = "{} have paid their respects {}".format(users, choice(HEARTS))
            else:
                first = True
                users = ""
                for userId in self.settings[sid][cid][KEY_USERS]:
                    userObj = discord.utils.get(ctx.message.server.members, id=userId)
                    if first:
                        users = "and {}".format(userObj.name)
                        first = False
                    else:
                        users = "{}, {}".format(userObj.name, users)
                message = "**{}** have paid their respects {}".format(users, choice(HEARTS))

            messageObj = await self.bot.say(message)
            self.settings[sid][cid][KEY_MSG] = messageObj

def setup(bot):
    """Add the cog to the bot."""
    customCog = Respects(bot)
    bot.add_cog(customCog)
