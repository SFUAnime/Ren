"""Spoilers cog
Filters out messages that start with a certain prefix, and store them for
later retrieval.
"""

from datetime import datetime, timedelta
import logging
import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO

from cogs.utils import config

# Global variables
KEY_MESSAGE = "message"
KEY_AUTHOR_ID = "authorid"
KEY_AUTHOR_NAME = "author"
KEY_TIMESTAMP = "timestamp"
LOGGER = None
PREFIX = "spoiler"
SAVE_FOLDER = "data/lui-cogs/spoilers/" # Path to save folder.
SAVE_FILE = "settings.json"
COOLDOWN = 60

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

def checkFiles():
    """Used to initialize an empty database at first startup"""
    theFile = SAVE_FOLDER + SAVE_FILE
    if not dataIO.is_valid_json(theFile):
        print("Creating default spoilers settings.json")
        dataIO.save_json(theFile, {})

class Spoilers: # pylint: disable=too-many-instance-attributes
    """Store messages for later retrieval."""

    #Class constructor
    def __init__(self, bot):
        self.bot = bot

        #The JSON keys for the settings:
        checkFolder()
        checkFiles()
        self.settings = config.Config("settings.json",
                                      cogname="lui-cogs/spoilers")
        self.messages = self.settings.get("messages") if not None else {}
        self.onCooldown = {}

    @commands.command(name="spoiler", pass_context=True)
    async def spoiler(self, ctx, *, msg):
        """Create a message spoiler."""
        store = {}
        store[KEY_MESSAGE] = msg
        store[KEY_AUTHOR_ID] = ctx.message.author.id
        store[KEY_AUTHOR_NAME] = "{0.name}#{0.discriminator}".format(ctx.message.author)
        store[KEY_TIMESTAMP] = ctx.message.timestamp.strftime("%s")
        await self.bot.delete_message(ctx.message)
        newMsg = await self.bot.say(":warning: {} created a spoiler!  React to see "
                                    "the message!".format(ctx.message.author.mention))
        if not self.messages:
            self.messages = {}
        self.messages[newMsg.id] = store
        LOGGER.info("%s#%s (%s) added a spoiler: %s",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id,
                    msg)
        await self.bot.add_reaction(newMsg, "\N{INFORMATION SOURCE}")
        await self.settings.put("messages", self.messages)

    async def checkForReaction(self, reaction, user):
        """Reaction listener
        Checks to see if a spoilered message is reacted, and if so, send a DM to the
        user that reacted.
        """
        # As per documentation, access the message via reaction.message.
        if user.bot:
            return
        msgId = reaction.message.id
        if msgId in self.messages.keys():
            await self.bot.remove_reaction(reaction.message,
                                           reaction.emoji,
                                           user)

            if (msgId in self.onCooldown.keys() and
                    user.id in self.onCooldown[msgId].keys() and
                    self.onCooldown[msgId][user.id] > datetime.now):
                return
            msg = self.messages[msgId]
            embed = discord.Embed()
            userObj = discord.utils.get(user.server.members,
                                        id=msg[KEY_AUTHOR_ID])
            if userObj:
                embed.set_author(name="{0.name}#{0.discriminator}".format(userObj),
                                 icon_url=userObj.avatar_url)
            else:
                embed.set_author(name=msg[KEY_AUTHOR_NAME])
            embed.description = msg[KEY_MESSAGE]
            embed.timestamp = datetime.fromtimestamp(int(msg[KEY_TIMESTAMP]))
            try:
                await self.bot.send_message(user, embed=embed)
                if msgId not in self.onCooldown.keys():
                    self.onCooldown[msgId] = {}
                self.onCooldown[msgId][user.id] = datetime.now() + timedelta(seconds=COOLDOWN)
            except discord.errors.Forbidden:
                LOGGER.error("Could not send DM to %s#%s (%s).",
                             user.name,
                             user.discriminator,
                             user.id)

def setup(bot):
    """Add the cog to the bot."""
    checkFolder()   # Make sure the data folder exists!
    checkFiles()    # Make sure we have settings!
    spoilersCog = Spoilers(bot)
    global LOGGER # pylint: disable=global-statement
    LOGGER = logging.getLogger("red.Spoilers")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/lui-cogs/spoilers/info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    bot.add_listener(spoilersCog.checkForReaction, "on_reaction_add")
    bot.add_cog(spoilersCog)
