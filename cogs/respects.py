"""Respects cog
A replica of +f seen in another bot, except smarter..
"""
import copy
import logging
import os
from datetime import datetime, timedelta
from threading import Lock
from random import choice
import discord
from discord.ext import commands
from cogs.utils import checks, config

KEY_USERS = "users"
KEY_TIME = "time"
KEY_MSG = "msg"
KEY_TIME_BETWEEN = "timeSinceLastRespect"
KEY_MSGS_BETWEEN = "msgsSinceLastRespect"
HEARTS = [":green_heart:", ":heart:", ":black_heart:", ":yellow_heart:",
          ":purple_heart:", ":blue_heart:"]
DEFAULT_CH_DICT = {KEY_MSG : None, KEY_TIME : None, KEY_USERS : []}
DEFAULT_TIME_BETWEEN = timedelta(seconds=30) # Time between paid respects.
DEFAULT_MSGS_BETWEEN = 20 # The number of messages in between
LOGGER = None
SAVE_FOLDER = "data/lui-cogs/respects/"
TEXT_RESPECTS = "paid their respects"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

class Respects:
    """Pay your respects."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot
        self.plusFLock = Lock()
        self.settingsLock = Lock()
        self.settings = {}
        self.config = config.Config("settings.json", cogname="lui-cogs/respects")

        timeBetween = self.config.get(KEY_TIME_BETWEEN)
        self.timeBetween = timedelta(seconds=timeBetween) if timeBetween else DEFAULT_TIME_BETWEEN

        msgsBetween = self.config.get(KEY_MSGS_BETWEEN)
        self.msgsBetween = msgsBetween if msgsBetween else DEFAULT_MSGS_BETWEEN

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
            try:
                await self.bot.delete_message(ctx.message)
            except (discord.Forbidden, discord.NotFound):
                await self.bot.say("I currently cannot delete messages. Please give me the"
                                   " \"Manage Messages\" permission to allow this feature to"
                                   " work!")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="setf", pass_context=True, no_pm=True)
    async def setf(self, ctx):
        """Respect settings."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @setf.command(name="messages", pass_context=True, no_pm=True)
    async def setfMessages(self, ctx, messages: int):
        """Set the number of messages that must appear before a new respect is paid.

        Parameters:
        -----------
        messages: int
            The number of messages between messages.  Should be between 1 and 100
        """
        if messages < 1 or messages > 100:
            await self.bot.say(":negative_squared_cross_mark: Please enter a number "
                               "between 1 and 100!")
            return
        self.msgsBetween = messages
        await self.config.put(KEY_MSGS_BETWEEN, self.msgsBetween)
        await self.bot.say(":white_check_mark: **Respects - Messages**: A new respect will be "
                           "created after **{}** messages and **{}** seconds have passed "
                           "since the previous one.".format(self.msgsBetween,
                                                            self.timeBetween.seconds))
        LOGGER.info("%s#%s (%s) changed the messages between respects to %s messages",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id,
                    messages)

    @setf.command(name="show", pass_context=False, no_pm=True)
    async def setfShow(self):
        """Show the current settings."""
        msg = ":information_source: **Respects - Current Settings:**\n"
        msg += "A new respect will be made if a previous respect does not exist, or:\n"
        msg += "- **{}** seconds have passed since the last respect, **and**\n"
        msg += "- **{}** messages have been passed since the last respect."
        await self.bot.say(msg.format(self.timeBetween.seconds, self.msgsBetween))

    @setf.command(name="time", pass_context=True, no_pm=True)
    async def setfTime(self, ctx, seconds: int):
        """Set the number of seconds that must pass before a new respect is paid.

        Parameters:
        -----------
        seconds: int
            The number of seconds that must pass.  Should be between 1 and 100
        """
        if seconds < 1 or seconds > 100:
            await self.bot.say(":negative_squared_cross_mark: Please enter a number "
                               "between 1 and 100!")
            return
        self.timeBetween = timedelta(seconds=seconds)
        await self.config.put(KEY_TIME_BETWEEN, seconds)
        await self.bot.say(":white_check_mark: **Respects - Time**: A new respect will be "
                           "created after **{}** messages and **{}** seconds have passed "
                           "since the previous one.".format(self.msgsBetween,
                                                            self.timeBetween.seconds))
        LOGGER.info("%s#%s (%s) changed the time between respects to %s seconds",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id,
                    seconds)


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
                                                limit=self.msgsBetween,
                                                before=ctx.message):
                prevMsgs.append(msg.id)

            if self.settings[sid][cid][KEY_MSG]:
                exceedMessages = self.settings[sid][cid][KEY_MSG].id not in prevMsgs
            else:
                exceedMessages = False
            exceedTime = datetime.now() - self.settings[sid][cid][KEY_TIME] > self.timeBetween

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
                except(discord.Forbidden, discord.NotFound):
                    await self.bot.say("I currently cannot delete messages, please give me \"Manage"
                                       " Message\" permissions to allow this feature to work!")
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
    global LOGGER # pylint: disable=global-statement
    checkFolder()
    LOGGER = logging.getLogger("red.Respects")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=SAVE_FOLDER+"info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    customCog = Respects(bot)
    bot.add_cog(customCog)
