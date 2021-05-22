"""Welcome cog
Sends welcome DMs to users that join the server.
"""

import asyncio
import discord
import logging
import random

from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import error, pagify, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils import AsyncIter

LOGGER = logging.getLogger("red.luicogs.Welcome")

KEY_DM_ENABLED = "dmEnabled"
KEY_LOG_JOIN_ENABLED = "logJoinEnabled"
KEY_LOG_JOIN_CHANNEL = "logJoinChannel"
KEY_LOG_LEAVE_ENABLED = "logLeaveEnabled"
KEY_LOG_LEAVE_CHANNEL = "logLeaveChannel"
KEY_TITLE = "title"
KEY_MESSAGE = "message"
KEY_IMAGE = "image"
KEY_GREETINGS = "greetings"
KEY_WELCOME_CHANNEL = "welcomeChannel"
KEY_WELCOME_CHANNEL_ENABLED = "welcomeChannelSet"

MAX_MESSAGE_LENGTH = 2000

DEFAULT_GUILD = {
    KEY_DM_ENABLED: False,
    KEY_LOG_JOIN_ENABLED: False,
    KEY_LOG_JOIN_CHANNEL: None,
    KEY_LOG_LEAVE_ENABLED: False,
    KEY_LOG_LEAVE_CHANNEL: None,
    KEY_TITLE: "Welcome!",
    KEY_MESSAGE: "Welcome to the server! Hope you enjoy your stay!",
    KEY_IMAGE: None,
    KEY_GREETINGS: {},
    KEY_WELCOME_CHANNEL: None,
    KEY_WELCOME_CHANNEL_ENABLED: False,
}


class Welcome(commands.Cog):  # pylint: disable=too-many-instance-attributes
    """Send a welcome DM on server join."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

    async def getRandomMessage(self, guild):
        greetings = await self.config.guild(guild).greetings()
        numGreetings = len(greetings)
        if not greetings:
            return "Welcome to the server {USER}"
        else:
            return random.choice(list(greetings.values()))

    # The async function that is triggered on new member join.
    @commands.Cog.listener()
    async def on_member_join(self, newMember: discord.Member):
        await self.sendWelcomeMessageChannel(newMember)
        await self.sendWelcomeMessage(newMember)

    @commands.Cog.listener()
    async def on_member_remove(self, leaveMember: discord.Member):
        await self.logServerLeave(leaveMember)

    # This async function is to look for if the welcome channel was removed
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, removedChannel: discord.TextChannel):
        if not isinstance(removedChannel, discord.TextChannel):
            return
        guild = removedChannel.guild
        # the channel to post welcome stuff in
        welcomeIDSet = await self.config.guild(guild).welcomeChannelSet()
        welcomeID = await self.config.guild(guild).welcomeChannel()
        if welcomeIDSet and removedChannel.id == welcomeID:
            await self.config.guild(guild).welcomeChannelSet.set(False)
            LOGGER.info("Changed guild's welcomeChannelSetFlag to false as channel was deleted")
        return

    async def sendWelcomeMessageChannel(self, newUser: discord.Member):
        guild = newUser.guild
        channelID = await self.config.guild(guild).welcomeChannel()
        isSet = await self.config.guild(guild).welcomeChannelSet()
        # if channel isn't set
        if not isSet:
            return
        channel = discord.utils.get(guild.channels, id=channelID)
        rawMessage = await self.getRandomMessage(guild)

        message = rawMessage.replace("{USER}", newUser.mention)
        splitMessage = rawMessage.split("{USER}")

        try:
            await channel.send(message)
        except (discord.Forbidden, discord.HTTPException) as errorMsg:
            LOGGER.error(
                "Could not send message, please make sure the bot "
                "has enough permissions to send messages to this "
                "channel!",
                exc_info=True,
            )
            LOGGER.error(errorMsg)
        else:
            LOGGER.info(
                "User %s#%s (%s) has joined. Posted welcome message.",
                newUser.name,
                newUser.discriminator,
                newUser.id,
            )

        return

    async def sendWelcomeMessage(self, newUser, test=False):
        """Sends the welcome message in DM."""
        async with self.config.guild(newUser.guild).all() as guildData:
            if not guildData[KEY_DM_ENABLED]:
                return

            welcomeEmbed = discord.Embed(title=guildData[KEY_TITLE])
            welcomeEmbed.description = guildData[KEY_MESSAGE]
            welcomeEmbed.colour = discord.Colour.red()
            if guildData[KEY_IMAGE]:
                imageUrl = guildData[KEY_IMAGE]
                welcomeEmbed.set_image(url=imageUrl.replace(" ", "%20"))

            channel = discord.utils.get(
                newUser.guild.text_channels, id=guildData[KEY_LOG_JOIN_CHANNEL]
            )

            try:
                await newUser.send(embed=welcomeEmbed)
            except (discord.Forbidden, discord.HTTPException) as errorMsg:
                LOGGER.error(
                    "Could not send message, the user may have"
                    "turned off DM's from this server."
                    " Also, make sure the server has a title "
                    "and message set!",
                    exc_info=True,
                )
                LOGGER.error(errorMsg)
                if guildData[KEY_LOG_JOIN_ENABLED] and not test and channel:
                    await channel.send(
                        ":bangbang: ``Server Welcome:`` User "
                        f"{newUser.name}#{newUser.discriminator} "
                        f"({newUser.id}) has joined. Could not send "
                        "DM!"
                    )
                    await channel.send(errorMsg)
            else:
                if guildData[KEY_LOG_JOIN_ENABLED] and not test and channel:
                    await channel.send(
                        f":o: ``Server Welcome:`` User {newUser.name}#"
                        f"{newUser.discriminator} ({newUser.id}) has "
                        "joined. DM sent."
                    )
                    LOGGER.info(
                        "User %s#%s (%s) has joined.  DM sent.",
                        newUser.name,
                        newUser.discriminator,
                        newUser.id,
                    )

    async def logServerLeave(self, leaveUser: discord.Member):
        """Logs the server leave to a channel, if enabled."""
        async with self.config.guild(leaveUser.guild).all() as guildData:
            if guildData[KEY_LOG_LEAVE_ENABLED]:
                channel = discord.utils.get(
                    leaveUser.guild.text_channels, id=guildData[KEY_LOG_LEAVE_CHANNEL]
                )
                if channel:
                    await channel.send(
                        f":x: ``Server Leave  :`` User {leaveUser.name}#"
                        f"{leaveUser.discriminator} ({leaveUser.id}) has "
                        "left the server."
                    )
                LOGGER.info(
                    "User %s#%s (%s) has left the server.",
                    leaveUser.name,
                    leaveUser.discriminator,
                    leaveUser.id,
                )

    ####################
    # MESSAGE COMMANDS #
    ####################

    # [p]welcome
    @commands.group(name="welcomeset")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def welcome(self, ctx: Context):
        """Server welcome message settings."""

    # [p]greetings
    @welcome.group(name="greetings")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def greetings(self, ctx: Context):
        """Server greetings message settings."""

    @checks.mod_or_permissions()
    @greetings.command(name="channel")
    async def welcomeChannelSet(self, ctx: Context, channel: discord.TextChannel = None):
        """
        Set the welcome channel

        Parameters:
        -----------
        channel: The text channel to set welcome's to. If not passed anything, will remove the welcome channel
        """
        if not channel:
            # channel == None
            await self.config.guild(ctx.guild).welcomeChannelSet.set(False)
            await ctx.send("Welcome channel has been removed")
            return

        await self.config.guild(ctx.guild).welcomeChannel.set(channel.id)
        await self.config.guild(ctx.guild).welcomeChannelSet.set(True)
        await ctx.send(f"Channel set to {channel}")

        return

    @checks.mod_or_permissions()
    @greetings.command(name="add")
    async def greetAdd(self, ctx: Context, name: str):
        """
        Add a new greeting

        Including {USER} in the message will have that replaced with a ping to the new user

        Parameters:
        -----------
        name: name of the greeting
        """

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        await ctx.send("What would you like the greeting message to be?")
        try:
            greeting = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        # check for if the message with a replaced {USER} will be too long
        tempmsg = greeting.content.replace("{USER}", ctx.author.mention)
        if len(tempmsg) > MAX_MESSAGE_LENGTH:
            await ctx.send("Your message is too long!")
            return

        greetings = await self.config.guild(ctx.guild).greetings()

        if name in greetings:
            await ctx.send(
                warning(
                    "This greeting already exists, overwrite it? Please type 'yes' to overwrite"
                )
            )
            try:
                response = await self.bot.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("You took too long, not overwriting")
                return

            if response.content.lower() != "yes":
                await ctx.send("Not overwriting the greeting")
                return

        # save the greetings
        greetings[name] = greeting.content
        await greeting.add_reaction("✅")
        await self.config.guild(ctx.guild).greetings.set(greetings)
        return

    @checks.mod_or_permissions()
    @greetings.command(name="remove", aliases=["delete", "del", "rm"])
    async def greetRemove(self, ctx: Context, name: str):
        """
        Remove a greeting

        Parameters:
        -----------
        name: name of the greeting to remove
        """

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        greetings = await self.config.guild(ctx.guild).greetings()
        if name in greetings:
            await ctx.send(
                warning("Are you sure you wish to delete this greeting? Respond with 'yes' if yes")
            )
            try:
                response = await self.bot.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("You took too long, not deleting")
                return

            if response.content.lower() != "yes":
                await ctx.send("Not deleting")
                return

            # delete the greeting
            del greetings[name]
            await ctx.send(f"{name} removed from list")
            await self.config.guild(ctx.guild).greetings.set(greetings)
        else:
            ctx.send(f"{name} not in list of greetings")
        return

    @checks.mod_or_permissions()
    @greetings.command(name="list", aliases=["ls"])
    async def greetList(self, ctx: Context):
        """
        List all greetings on the server
        """
        greetings = await self.config.guild(ctx.guild).greetings()

        if not greetings:
            await ctx.send("There are no greetings, please add some first!")
            return

        msg = ""

        for name, greeting in greetings.items():
            msg += f"{name}: {greeting}\n"

        pageList = []
        pages = list(pagify(msg, page_length=500))
        totalPages = len(pages)
        async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
            embed = discord.Embed(
                title=f"Welcome greetings changes for {ctx.guild.name}", description=page
            )
            embed.set_footer(text=f"Page {pageNumber}/{totalPages}")
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    # [p]welcome setmessage
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

        if len(message.content) > MAX_MESSAGE_LENGTH:
            await ctx.send("Your message is too long!")
            return

        await self.config.guild(ctx.guild).message.set(message.content)
        await ctx.send("Message set to:")
        await ctx.send(f"```{message.content}```")
        LOGGER.info(
            "Message changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        LOGGER.info(message.content)

    # [p]welcome toggledm
    @welcome.command(name="dm", aliases=["toggledm"])
    async def toggledm(self, ctx: Context):
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
            LOGGER.info(
                "Message toggle ENABLED by %s#%s (%s)",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
            )
        else:
            await ctx.send(":negative_squared_cross_mark: Server Welcome - DM: " "Disabled.")
            LOGGER.info(
                "Message toggle DISABLED by %s#%s (%s)",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
            )

    # [p]welcome togglelog
    @welcome.command(name="log", aliases=["togglelog"])
    async def toggleLog(self, ctx: Context):
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
            await ctx.send(":white_check_mark: Server Welcome/Leave - Logging: " "Enabled.")
            LOGGER.info(
                "Welcome channel logging ENABLED by %s#%s (%s)",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
            )
        else:
            await ctx.send(
                ":negative_squared_cross_mark: Server Welcome/Leave " "- Logging: Disabled."
            )
            LOGGER.info(
                "Welcome channel logging DISABLED by %s#%s (%s)",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
            )

    # [p]welcome logchannel
    @welcome.command(name="logchannel", aliases=["logch"])
    async def setLogChannel(self, ctx: Context, channel: discord.TextChannel = None):
        """Set log channel. Defaults to current channel.

        Parameters:
        -----------
        channel: discord.TextChannel (optional)
            The channel to log member join and leaves. Defaults to current channel.
        """
        if not channel:
            channel = ctx.channel
        async with self.config.guild(ctx.guild).all() as guildData:
            guildData[KEY_LOG_JOIN_CHANNEL] = channel.id
            guildData[KEY_LOG_LEAVE_CHANNEL] = channel.id
        await ctx.send(
            ":white_check_mark: Server Welcome/Leave - Logging: "
            f"Member join/leave will be logged to {channel.name}."
        )
        LOGGER.info(
            "Welcome channel changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        LOGGER.info(
            "Welcome channel set to #%s (%s)", ctx.message.channel.name, ctx.message.channel.id
        )

    # [p]welcome title
    @welcome.command(name="title")
    async def setTitle(self, ctx: Context):
        """Interactively configure the title for the welcome DM."""
        await ctx.send("What would you like the welcome DM title to be?")

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        try:
            title = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        if len(title.content) > 256:
            await ctx.send("The title is too long!")
            return

        await self.config.guild(ctx.guild).title.set(title.content)
        await ctx.send("Title set to:")
        await ctx.send(f"```{title.content}```")
        LOGGER.info(
            "Title changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author,
        )
        LOGGER.info(title.content)

    # [p]welcome setimage
    @welcome.command(name="image")
    async def setImage(self, ctx: Context, imageUrl: str = None):
        """Sets an image in the embed with a URL.

        Parameters:
        -----------
        imageUrl: str (optional)
            The URL of the image to use in the DM embed. Leave blank to disable.
        """
        if imageUrl == "":
            imageUrl = None

        await self.config.guild(ctx.guild).image.set(imageUrl)
        if imageUrl:
            await ctx.send(f"Welcome image set to `{imageUrl}`. Be sure to test it!")
        else:
            await ctx.send("Welcome image disabled.")
        LOGGER.info(
            "Image changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.id,
        )
        LOGGER.info("Image set to %s", imageUrl)

    # [p]welcome test
    @welcome.command(name="test")
    async def test(self, ctx: Context):
        """Test the welcome DM by sending a DM to you."""
        await self.sendWelcomeMessage(ctx.message.author, test=True)
        await ctx.send("If this server has been configured, you should have received a DM.")
