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
from cogs.utils import checks

#Global variables

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
        print("Creating default spoilers settings.json...")
        dataIO.save_json(theFile, {})

class Spoilers: # pylint: disable=too-many-instance-attributes
    """Store messages for later retrieval."""


    def loadSettings(self):
        """Loads settings from the JSON file"""
        self.settings = dataIO.load_json(SAVE_FOLDER+SAVE_FILE)

    def saveSettings(self):
        """Loads settings from the JSON file"""
        dataIO.save_json(SAVE_FOLDER+SAVE_FILE, self.settings)

    #Class constructor
    def __init__(self, bot):
        self.bot = bot

        #The JSON keys for the settings:
        checkFolder()
        checkFiles()
        self.loadSettings()

    async def checkForMessage(self, msg, newMsg=None):
        pass

    async def checkForReaction(self, reaction, user):
        # As per documentation, access the message via reaction.message.
        pass

def setup(bot):
    """Add the cog to the bot."""
    checkFolder()   #Make sure the data folder exists!
    checkFiles()    #Make sure we have settings!
    spoilersCog = Spoilers(bot)
    bot.add_listener(spoilersCog.checkForMessage, "on_message")
    bot.add_listener(spoilersCog.checkForMessage, "on_message_edit")
    bot.add_listener(spoilersCog.checkForReaction, "on_reaction_add")
    bot.add_cog(spoilersCog)
