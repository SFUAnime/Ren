"""Welcome cog
Sends welcome DMs to users that join the server.
"""

import discord
import logging

from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context

#Global variables

LOGGER = None

KEY_DM_ENABLED = "dmEnabled"
KEY_LOG_JOIN_ENABLED = "logJoinEnabled"
KEY_LOG_JOIN_CHANNEL = "logJoinChannel"
KEY_LOG_LEAVE_ENABLED = "logLeaveEnabled"
KEY_LOG_LEAVE_CHANNEL = "logLeaveChannel"
KEY_TITLE = "title"
KEY_MESSAGE = "message"
KEY_IMAGE = "image"

DEFAULT_GUILD= \
{
    KEY_DM_ENABLED: False,
    KEY_LOG_JOIN_ENABLED: False,
    KEY_LOG_JOIN_CHANNEL: None,
    KEY_LOG_LEAVE_ENABLED: False,
    KEY_LOG_LEAVE_CHANNEL: None,
    KEY_TITLE: "Welcome!",
    KEY_MESSAGE: "Welcome to the server! Hope you enjoy your stay!",
    KEY_IMAGE: None,
}

class Welcome(commands.Cog): # pylint: disable=too-many-instance-attributes
    """Send a welcome DM on server join."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self,
                                      identifier=5842647,
                                      force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

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
            if self.keyWelcomeImage in self.settings[serverId].keys() and \
                    self.settings[serverId][self.keyWelcomeImage]:
                imageUrl = self.settings[serverId][self.keyWelcomeImage]
                welcomeEmbed.set_image(url=imageUrl.replace(" ", "%20"))
            await self.bot.send_message(newUser, embed=welcomeEmbed)
        except (discord.Forbidden, discord.HTTPException) as errorMsg:
            LOGGER.error("Could not send message, the user may have"
                         "turned off DM's from this server."
                         " Also, make sure the server has a title "
                         "and message set!", exc_info=True)
            LOGGER.error(errorMsg)
            if self.settings[serverId][self.keyWelcomeLogEnabled] and not test:
                channel = self.bot.get_channel(self.settings[serverId][self.keyWelcomeLogChannel])
                await self.bot.send_message(channel,
                                            ":bangbang: ``Server Welcome:`` User "
                                            "{0.name}#{0.discriminator} ({0.id}) has"
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
    @commands.group(name="welcome")
    @commands.guild_only()
    @checks.guildowner()
    async def welcome(self, ctx: Context):
        """Server welcome message settings."""

    #[p]welcome setmessage
    @welcome.command(name="message", aliases=["msg"])
    async def setmessage(self, ctx: Context):
        """Interactively configure the contents of the welcome DM."""
        await ctx.send("What would you like the welcome DM message to be?")

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        try:
            message = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        if len(message.content) > 2048:
            await ctx.send("Your message is too long!")
            return

        await self.config.guild(ctx.guild).message.set(message.content)
        await ctx.send("Message set to:")
        await ctx.send(f"```{message.content}```")
        # LOGGER.info("Message changed by %s#%s (%s)",
        #             ctx.message.author.name,
        #             ctx.message.author.discriminator,
        #             ctx.message.author.id)
        # LOGGER.info(message.content)

    #[p]welcome toggledm
    @welcome.command(name="dm", aliases=["toggledm"])
    @checks.guildowner()
    async def toggledm(self, ctx):
        """Toggle sending a welcome DM."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_DM_ENABLED]:
                guildData[KEY_DM_ENABLED] = False
                isSet = False
            else:
                guildData[KEY_DM_ENABLED] = True
                isSet = True
        if isSet:
            await ctx.send(":white_check_mark: Server Welcome - DM: Enabled.")
            # LOGGER.info("Message toggle ENABLED by %s#%s (%s)",
            #             ctx.message.author.name,
            #             ctx.message.author.discriminator,
            #             ctx.message.author.id)
        else:
            await ctx.send(":negative_squared_cross_mark: Server Welcome - DM: "
                           "Disabled.")
            # LOGGER.info("Message toggle DISABLED by %s#%s (%s)",
            #             ctx.message.author.name,
            #             ctx.message.author.discriminator,
            #             ctx.message.author.id)

    #[p]welcome togglelog
    @welcome.command(name="log", aliases=["togglelog"])
    @checks.guildowner()
    async def toggleLog(self, ctx):
        """Toggle sending logs to a channel."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if not guildData[KEY_LOG_JOIN_CHANNEL] or not guildData[KEY_LOG_LEAVE_CHANNEL]:
                await ctx.send(":negative_squared_cross_mark: Please set a log channel first!")
                return
            if guildData[KEY_LOG_JOIN_ENABLED]:
                guildData[KEY_LOG_JOIN_ENABLED] = False
                guildData[KEY_LOG_LEAVE_ENABLED] = False
                isSet = False
            else:
                guildData[KEY_LOG_JOIN_ENABLED] = True
                guildData[KEY_LOG_LEAVE_ENABLED] = True
                isSet = True
        if isSet:
            await ctx.send(":white_check_mark: Server Welcome/Leave - Logging: "
                           "Enabled.")
            # LOGGER.info("Welcome channel logging ENABLED by %s#%s (%s)",
            #             ctx.message.author.name,
            #             ctx.message.author.discriminator,
            #             ctx.message.author.id)
        else:
            await ctx.send(":negative_squared_cross_mark: Server Welcome/Leave "
                           "- Logging: Disabled.")
            # LOGGER.info("Welcome channel logging DISABLED by %s#%s (%s)",
            #             ctx.message.author.name,
            #             ctx.message.author.discriminator,
            #             ctx.message.author.id)

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
