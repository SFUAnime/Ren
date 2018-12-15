"""Welcome cog
Sends welcome DMs to users that join the server.
"""

import os
import logging
import discord
from discord.ext import commands
from __main__ import send_cmd_help # pylint: disable=no-name-in-module
from cogs.utils.dataIO import dataIO

# Requires checks utility from:
# https://github.com/Rapptz/RoboDanny/tree/master/cogs/utils
from cogs.utils import checks

#Global variables

DEFAULT_MESSAGE = "Welcome to the server! Hope you enjoy your stay!"
DEFAULT_TITLE = "Welcome!"
LOGGER = None
SAVE_FOLDER = "data/lui-cogs/welcome/" #Path to save folder.
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
        print("Creating default welcome settings.json...")
        dataIO.save_json(theFile, {})

class Welcome: # pylint: disable=too-many-instance-attributes
    """Send a welcome DM on server join."""


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
        self.keyWelcomeDMEnabled = "welcomeDMEnabled"
        self.keyWelcomeLogEnabled = "welcomeLogEnabled"
        self.keyWelcomeLogChannel = "welcomeLogChannel"
        self.keyWelcomeTitle = "welcomeTitle"
        self.keyWelcomeMessage = "welcomeMessage"
        self.keyWelcomeImage = "welcomeImage"

        self.keyLeaveLogEnabled = "leaveLogEnabled"
        self.keyLeaveLogChannel = "leaveLogChannel"

        checkFolder()
        checkFiles()
        self.loadSettings()

    #The async function that is triggered on new member join.
    async def sendWelcomeMessage(self, newUser, test=False):
        """Sends the welcome message in DM."""

        serverId = newUser.server.id
        #Do not send DM if it is disabled!
        if not self.settings[serverId][self.keyWelcomeDMEnabled]:
            return

        try:
            welcomeEmbed = discord.Embed(title=self.settings[serverId][self.keyWelcomeTitle])
            welcomeEmbed.description = self.settings[serverId][self.keyWelcomeMessage]
            welcomeEmbed.colour = discord.Colour.red()
            if self.settings[serverId][self.keyWelcomeImage]:
                imageUrl = self.settings[serverId][self.keyWelcomeImage]
                welcomeEmbed.set_image(url=imageUrl.replace(" ", "%20"))
            await self.bot.send_message(newUser, embed=welcomeEmbed)
        except (discord.Forbidden, discord.HTTPException) as errorMsg:
            LOGGER.error("Could not send message, make sure the server has a title "
                         "and message set!")
            LOGGER.error(errorMsg)
            if self.settings[serverId][self.keyWelcomeLogEnabled] and not test:
                channel = self.bot.get_channel(self.settings[serverId][self.keyWelcomeLogChannel])
                await self.bot.send_message(channel,
                                            ":bangbang: ``Server Welcome:`` User "
                                            "{0.name}#{0.descriminator} ({0.id}) has"
                                            " joined.  Could not send DM!".format(
                                                newUser))
                await self.bot.send_message(channel, errorMsg)
        else:
            if self.settings[serverId][self.keyWelcomeLogEnabled] and not test:
                channel = self.bot.get_channel(self.settings[serverId][self.keyWelcomeLogChannel])
                await self.bot.send_message(channel,
                                            ":o: ``Server Welcome:`` User {0.name}#"
                                            "{0.discriminator} ({0.id}) has joined. "
                                            "DM sent.".format(newUser))
                LOGGER.info("User %s#%s (%s) has joined.  DM sent.",
                            newUser.name,
                            newUser.discriminator,
                            newUser.id)

    async def logServerLeave(self, leaveUser):
        """Logs the server leave to a channel, if enabled."""
        serverId = leaveUser.server.id
        if self.settings[serverId][self.keyLeaveLogEnabled]:
            channel = self.bot.get_channel(self.settings[serverId][self.keyLeaveLogChannel])
            await self.bot.send_message(channel,
                                        ":x: ``Server Leave  :`` User {0.name}#"
                                        "{0.discriminator} ({0.id}) has left the "
                                        "server.".format(leaveUser))
            LOGGER.info("User %s#%s (%s) has left the server.",
                        leaveUser.name,
                        leaveUser.discriminator,
                        leaveUser.id)

    ####################
    # MESSAGE COMMANDS #
    ####################

    #[p]welcome
    @commands.group(name="welcome", pass_context=True, no_pm=False)
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def _welcome(self, ctx):
        """Server welcome message settings."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    #[p]welcome setmessage
    @_welcome.command(pass_context=True, no_pm=False)
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def setmessage(self, ctx):
        """Interactively configure the contents of the welcome DM."""

        await self.bot.say("What would you like the welcome DM message to be?")
        message = await self.bot.wait_for_message(timeout=60,
                                                  author=ctx.message.author,
                                                  channel=ctx.message.channel)

        if message is None:
            await self.bot.say("No response received, not setting anything!")
            return

        if len(message.content) > 2048:
            await self.bot.say("Your message is too long!")
            return

        try:
            self.loadSettings()
            if ctx.message.author.server.id in self.settings:
                self.settings[ctx.message.author.server.id] \
                    [self.keyWelcomeMessage] = message.content
            else:
                self.settings[ctx.message.author.server.id] = {}
                self.settings[ctx.message.author.server.id] \
                    [self.keyWelcomeMessage] = message.content
            self.saveSettings()
        except Exception as errorMsg: # pylint: disable=broad-except
            await self.bot.say("Could not save settings! Check the console for "
                               "details.")
            print(errorMsg)
        else:
            await self.bot.say("Message set to:")
            await self.bot.say("```" + message.content + "```")
            LOGGER.info("Message changed by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)
            LOGGER.info(message.content)

    #[p]welcome toggledm
    @_welcome.command(pass_context=True, no_pm=False)
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def toggledm(self, ctx):
        """Toggle sending a welcome DM."""
        self.loadSettings()
        try:
            if self.settings[ctx.message.author.server.id][self.keyWelcomeDMEnabled]:
                self.settings[ctx.message.author.server.id][self.keyWelcomeDMEnabled] = False
                isSet = False
            else:
                self.settings[ctx.message.author.server.id][self.keyWelcomeDMEnabled] = True
                isSet = True
        except KeyError:
            self.settings[ctx.message.author.server.id][self.keyWelcomeDMEnabled] = True
            isSet = True
        self.saveSettings()
        if isSet:
            await self.bot.say(":white_check_mark: Server Welcome - DM: Enabled.")
            LOGGER.info("Message toggle ENABLED by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)
        else:
            await self.bot.say(":negative_squared_cross_mark: Server Welcome - DM: "
                               "Disabled.")
            LOGGER.info("Message toggle DISABLED by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)

    #[p]welcome togglelog
    @_welcome.command(pass_context=True, no_pm=False, name="togglelog")
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def toggleLog(self, ctx):
        """Toggle sending logs to a channel."""
        self.loadSettings()

        #If no channel is set, send error.
        if not self.settings[ctx.message.author.server.id][self.keyWelcomeLogChannel] \
            or not self.settings[ctx.message.author.server.id][self.keyLeaveLogChannel]:
            await self.bot.say(":negative_squared_cross_mark: Please set a log channel first!")
            return

        try:
            if self.settings[ctx.message.author.server.id][self.keyWelcomeLogEnabled]:
                self.settings[ctx.message.author.server.id][self.keyWelcomeLogEnabled] = False
                self.settings[ctx.message.author.server.id][self.keyLeaveLogEnabled] = False
                isSet = False
            else:
                self.settings[ctx.message.author.server.id][self.keyWelcomeLogEnabled] = True
                self.settings[ctx.message.author.server.id][self.keyLeaveLogEnabled] = True
                isSet = True
        except KeyError:
            self.settings[ctx.message.author.server.id][self.keyWelcomeLogEnabled] = True
            self.settings[ctx.message.author.server.id][self.keyLeaveLogEnabled] = True
            isSet = True

        self.saveSettings()
        if isSet:
            await self.bot.say(":white_check_mark: Server Welcome/Leave - Logging: "
                               "Enabled.")
            LOGGER.info("Welcome channel logging ENABLED by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)
        else:
            await self.bot.say(":negative_squared_cross_mark: Server Welcome/Leave "
                               "- Logging: Disabled.")
            LOGGER.info("Welcome channel logging DISABLED by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)

    #[p]welcome setlog
    @_welcome.command(pass_context=True, no_pm=True, name="setlog")
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def setLog(self, ctx):
        """Enables, and sets current channel as log channel."""
        self.loadSettings()
        serverId = ctx.message.author.server.id
        try:
            self.settings[serverId][self.keyWelcomeLogChannel] = ctx.message.channel.id
            self.settings[serverId][self.keyWelcomeLogEnabled] = True
            self.settings[serverId][self.keyLeaveLogChannel] = ctx.message.channel.id
            self.settings[serverId][self.keyLeaveLogEnabled] = True
        except KeyError as errorMsg: #Typically a KeyError
            await self.bot.say(":negative_squared_cross_mark: Please set default "
                               "settings first!")
            print(errorMsg)
        else:
            self.saveSettings()
            await self.bot.say(":white_check_mark: Server Welcome/Leave - Logging: "
                               "Enabled, and will be logged to this channel only.")
            LOGGER.info("Welcome channel changed by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author.id)
            LOGGER.info("Welcome channel set to #%s (%s)",
                        ctx.message.channel.name,
                        ctx.message.channel.id)

    #[p]welcome default
    @_welcome.command(pass_context=True, no_pm=False)
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def default(self, ctx):
        """RUN FIRST: Set defaults, and enables welcome DM.  Will ask for confirmation."""
        await self.bot.say("Are you sure you want to revert to default settings? "
                           "Type \"yes\", otherwise type something else.")
        message = await self.bot.wait_for_message(timeout=60,
                                                  author=ctx.message.author,
                                                  channel=ctx.message.channel)

        if message is None:
            await self.bot.say(":no_entry: No response received, aborting.")
            return

        if str.lower(message.content) == "yes":
            try:
                self.loadSettings()
                serverId = ctx.message.author.server.id
                self.settings[serverId] = {}
                self.settings[serverId][self.keyWelcomeMessage] = DEFAULT_MESSAGE
                self.settings[serverId][self.keyWelcomeTitle] = DEFAULT_TITLE
                self.settings[serverId][self.keyWelcomeImage] = None
                self.settings[serverId][self.keyWelcomeDMEnabled] = True
                self.settings[serverId][self.keyWelcomeLogEnabled] = False
                self.settings[serverId][self.keyWelcomeLogChannel] = None
                self.settings[serverId][self.keyLeaveLogEnabled] = False
                self.settings[serverId][self.keyLeaveLogChannel] = None
                self.saveSettings()
            except Exception as errorMsg: # pylint: disable=broad-except
                await self.bot.say(":no_entry: Could not set default settings! "
                                   "Please check the server logs.")
                print(errorMsg)
            else:
                await self.bot.say(":white_check_mark: Default settings applied.")
                LOGGER.info("Welcome cog set to its defaults by %s#%s (%s)",
                            ctx.message.author.name,
                            ctx.message.author.discriminator,
                            ctx.message.author.id)
        else:
            await self.bot.say(":negative_squared_cross_mark: Not setting any "
                               "default settings.")


    #[p]welcome settitle
    @_welcome.command(pass_context=True, no_pm=False, name="settitle")
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def setTitle(self, ctx):
        """Interactively configure the title for the welcome DM."""

        await self.bot.say("What would you like the welcome DM message to be?")
        title = await self.bot.wait_for_message(timeout=60,
                                                author=ctx.message.author,
                                                channel=ctx.message.channel)

        if title is None:
            await self.bot.say("No response received, not setting anything!")
            return

        if len(title.content) > 256:
            await self.bot.say("The title is too long!")
            return

        try:
            self.loadSettings()
            serverId = ctx.message.author.server.id
            if serverId in self.settings:
                self.settings[serverId][self.keyWelcomeTitle] = title.content
            else:
                self.settings[serverId] = {}
                self.settings[serverId][self.keyWelcomeTitle] = title.content
            self.saveSettings()
        except Exception as errorMsg: # pylint: disable=broad-except
            await self.bot.say("Could not save settings! Please check server logs!")
            print(errorMsg)
        else:
            await self.bot.say("Title set to:")
            await self.bot.say("```" + title.content + "```")
            LOGGER.info("Title changed by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.author)
            LOGGER.info(title.content)

    #[p]welcome setimage
    @_welcome.group(name="setimage", pass_context=True, no_pm=True)
    async def setImage(self, ctx, imageUrl: str = None):
        """Sets an image in the embed with a URL.  Empty URL results in no image."""
        if imageUrl == "":
            imageUrl = None

        try:
            self.loadSettings()
            serverId = ctx.message.author.server.id
            if serverId in self.settings:
                self.settings[serverId][self.keyWelcomeImage] = imageUrl
            else:
                self.settings[serverId] = {}
                self.settings[serverId][self.keyWelcomeImage] = imageUrl
            self.saveSettings()
        except Exception as errorMsg: # pylint: disable=broad-except
            await self.bot.say("Could not save settings! Please check server logs!")
            print(errorMsg)
        else:
            await self.bot.say("Image set to `{}`. Be sure to test it!".format(imageUrl))
            LOGGER.info("Image changed by %s#%s (%s)",
                        ctx.message.author.name,
                        ctx.message.author.discriminator,
                        ctx.message.id)
            LOGGER.info("Image set to %s",
                        imageUrl)

   #[p]welcome test
    @_welcome.command(pass_context=True, no_pm=False)
    @checks.serverowner() #Only allow server owner to execute the following command.
    async def test(self, ctx):
        """Test the welcome DM by sending a DM to you."""
        await self.sendWelcomeMessage(ctx.message.author, test=True)
        await self.bot.say("If this server has been configured, you should have received a DM.")


def setup(bot):
    """Add the cog to the bot."""
    global LOGGER # pylint: disable=global-statement
    checkFolder()   #Make sure the data folder exists!
    checkFiles()    #Make sure we have settings!
    customCog = Welcome(bot)
    LOGGER = logging.getLogger("red.Welcome")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=SAVE_FOLDER+"info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    bot.add_listener(customCog.sendWelcomeMessage, 'on_member_join')
    bot.add_listener(customCog.logServerLeave, 'on_member_remove')
    bot.add_cog(customCog)
