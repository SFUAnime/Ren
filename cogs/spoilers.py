"""Spoilers cog
Filters out messages that start with a certain prefix, and store them for
later retrieval.
"""

import os
import discord
from discord.ext import commands
from __main__ import send_cmd_help # pylint: disable=no-name-in-module
from cogs.utils.dataIO import dataIO

# Requires checks utility from:
# https://github.com/Rapptz/RoboDanny/tree/master/cogs/utils
from cogs.utils import config, checks

#Global variables
KEY_MESSAGE = "message"
KEY_AUTHOR_ID = "authorid"
KEY_AUTHOR_NAME = "author"
PREFIX = "spoiler"
SAVE_FOLDER = "data/lui-cogs/spoilers/" #Path to save folder.
SAVE_FILE = "settings.json"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

def checkFiles():
    """Used to initialize an empty database at first startup"""
    theFile = SAVE_FOLDER + SAVE_FILE
    if not dataIO.is_valid_json(theFile):
        print("Creating default spoilers {}...".format(myFile))
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

    async def checkForMessage(self, msg, newMsg=None):
        """Message listener
        CHecks to see if the message contains the prefix, and if it does, it saves it
        for later retrieval.
        """
        if msg.author.bot or not msg.content:
            return
        split = msg.content.split()
        if split[0] == PREFIX:
            split.pop(0)
            store = {}
            store[KEY_MESSAGE] = " ".join(split)
            store[KEY_AUTHOR_ID] = msg.author.id
            store[KEY_AUTHOR_NAME] = "{}#{}".format(msg.author.name,
                                                    msg.author.discriminator)
            await self.bot.delete_message(msg)
            newMsg = await self.bot.send_message(msg.channel,
                                                 ":warning: {} created a spoiler!  React to see "
                                                 "the message!".format(msg.author.mention))
            if not self.messages:
                self.messages = {}
            self.messages[newMsg.id] = store
            await self.settings.put("messages", self.messages)

    async def checkForReaction(self, reaction, user):
        """Reaction listener
        Checks to see if a spoilered message is reacted, and if so, send a DM to the
        user that reacted.
        """
        # As per documentation, access the message via reaction.message.
        msgId = reaction.message.id
        if msgId in self.messages.keys():
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
            await self.bot.send_message(user, embed=embed)

def setup(bot):
    """Add the cog to the bot."""
    checkFolder()   #Make sure the data folder exists!
    checkFiles()    #Make sure we have settings!
    spoilersCog = Spoilers(bot)
    bot.add_listener(spoilersCog.checkForMessage, "on_message")
    bot.add_listener(spoilersCog.checkForMessage, "on_message_edit")
    bot.add_listener(spoilersCog.checkForReaction, "on_reaction_add")
    bot.add_cog(spoilersCog)
