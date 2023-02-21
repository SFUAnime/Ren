"""Welcome cog
Sends welcome DMs to users that join the server.
"""
import asyncio
import discord
import logging
import random
import aiohttp
import os
import io

from PIL import Image, ImageChops, ImageOps
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import box, info, pagify, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils import AsyncIter
from typing import Optional

from .constants import *
from .helpers import createTagListPages

LOGGER = logging.getLogger("red.luicogs.Welcome")


class Welcome(commands.Cog):  # pylint: disable=too-many-instance-attributes
    """Send a welcome DM on server join."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)

        self.config.register_guild(**DEFAULT_GUILD)

        self.data_dir = data_manager.cog_data_path(cog_instance=self)
        self.img_dir = self.data_dir / WELCOME_IMG_FOLDER
        self.bundled_assets = data_manager.bundled_data_path(self)

        # create folder to hold welcome images
        try:
            self.img_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            LOGGER.error(
                "Could not create folder for images!",
                exc_info=True,
            )

    async def getRandomMessage(self, guild: discord.Guild, pool: Optional[GreetingPools] = None):
        """Gets a random message from a greeting pool.

        If no pool is specified, the default pool is used.
        If the specified pool is empty, the default pool is used.

        Parameters
        ----------
        guild: discord.Guild
            The guild to get a random greeting from.
        pool: Optional[GreetingPools]
            The pool to get a random greeting from.
        """
        key = KEY_GREETINGS
        if pool == GreetingPools.RETURNING:
            key = KEY_RETURNING_GREETINGS

        greetings = await self.config.guild(guild).get_attr(key)()

        if not greetings:
            greetings = await self.config.guild(guild).get_attr(KEY_GREETINGS)()

        if not greetings:
            return "Welcome to the server {USER}"
        else:
            return random.choice(list(greetings.values()))

    # The async function that is triggered on new member join.
    @commands.Cog.listener()
    async def on_member_join(self, newMember: discord.Member):
        await self.sendWelcomeMessageChannel(newMember)
        await self.sendWelcomeMessage(newMember)
        await self.sendLogUserDescription(newMember)
        await self.addToJoinedUserIds(newMember)

    @commands.Cog.listener()
    async def on_member_remove(self, leaveMember: discord.Member):
        await self.logServerLeave(leaveMember)
        await self.sendLogUserDescription(leaveMember)
        # for those who were not encountered by the cog on joining the guild
        await self.addToJoinedUserIds(leaveMember)

    # This async function is to look for if the welcome channel was removed
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, removedChannel: discord.TextChannel):
        if not isinstance(removedChannel, discord.TextChannel):
            return
        guild = removedChannel.guild
        # the channel to post welcome stuff in
        welcomeIDSet = await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL_ENABLED)()
        welcomeID = await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL)()
        if welcomeIDSet and removedChannel.id == welcomeID:
            await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL_ENABLED).set(False)
            LOGGER.info("Changed guild's welcomeChannelSetFlag to false as channel was deleted")
        return

    async def sendToWelcomeChannel(self, guild: discord.Guild, *args, **kwargs):
        """
        Sends a message to the welcome channel of a guild.

        Parameters
        ----------
        guild: discord.Guild
            The guild to send the message to
        *args:
            The arguments to pass to the `discord.TextChannel.send()` method
        **kwargs:
            Keyword arguments to be passed to the `discord.TextChannel.send()` method

        Returns
        -------
        discord.Message
            The message sent

        Raises
        ------
        discord.Forbidden
            If the bot doesn't have permissions to send messages to the channel
        discord.HTTPException
            If the message couldn't be sent
        discord.InvalidArgument
            If keyword arguments are invalid
        ValueError
            If the welcome channel for the specified guild is not found.
        """

        welcomeChannelId: int = await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL)()

        if welcomeChannelId is None:
            raise ValueError(f"No welcome channel set for guild {guild.name} ({guild.id}).")

        welcomeChannel: discord.TextChannel = discord.utils.get(
            guild.text_channels, id=welcomeChannelId
        )

        if not welcomeChannel:
            raise ValueError(f"Welcome channel not found for guild {guild.name} ({guild.id})")

        return await welcomeChannel.send(*args, **kwargs)

    async def addToJoinedUserIds(self, newUser: discord.Member):
        """Adds the user's id to the list of joined users."""
        async with self.config.guild(newUser.guild).get_attr(
            KEY_JOINED_USER_IDS
        )() as joinedUserIds:
            if newUser.id not in joinedUserIds:
                joinedUserIds.append(newUser.id)

    async def isReturningUser(self, user: discord.Member):
        """Checks if the user is a returning user."""
        return user.id in await self.config.guild(user.guild).get_attr(KEY_JOINED_USER_IDS)()

    async def sendWelcomeMessageChannel(self, newUser: discord.Member):
        """Sends a welcome message to the welcome channel if it is set."""
        guild = newUser.guild
        channelID = await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL)()
        isSet = await self.config.guild(guild).get_attr(KEY_WELCOME_CHANNEL_ENABLED)()
        # if channel isn't set
        if not isSet:
            print("not set")
            return
        channel = discord.utils.get(guild.channels, id=channelID)

        greetingPool = GreetingPools.DEFAULT
        if await self.isReturningUser(newUser):
            greetingPool = GreetingPools.RETURNING

        rawMessage = await self.getRandomMessage(guild, pool=greetingPool)

        message = rawMessage.replace("{USER}", newUser.mention)

        try:
            img = await self.generateRandWelcomeImg(newUser)
            if await self.config.guild(guild).get_attr(KEY_TOGGLE_RANDOM_MSG)():
                await channel.send(message, file=discord.File(img, filename="generated.png"))
            else:
                await channel.send(message)
            img.close()
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

    async def sendWelcomeMessage(self, newUser: discord.Member, test=False):
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
                        f":bangbang: ``Server Welcome:`` User {newUser.mention} "
                        f"{newUser.name}#{newUser.discriminator} "
                        f"({newUser.id}) has joined. Could not send DM!"
                    )
                    await channel.send(errorMsg)

                doPostFailedDm = guildData[KEY_WELCOME_CHANNEL_SETTINGS][KEY_POST_FAILED_DM]
                if doPostFailedDm and not test:
                    infoMsg = (
                        f"Hey {newUser.mention}, we couldn't reach your DMs.\n"
                        "The following is what we wanted to send to you."
                    )
                    try:
                        await self.sendToWelcomeChannel(newUser.guild, infoMsg, embed=welcomeEmbed)
                    except ValueError as errorMsg:
                        LOGGER.error(
                            "Could not send messages to the welcome channel! "
                            "Please make sure welcome channel settings are "
                            "well configured!",
                            exc_info=True,
                        )
                        LOGGER.error(errorMsg)
                    except (discord.Forbidden, discord.HTTPException) as errorMsg:
                        LOGGER.error(
                            "Could not send message, please make sure the bot "
                            "has enough permissions to send messages to this "
                            "channel!",
                            exc_info=True,
                        )
                        LOGGER.error(errorMsg)
            else:
                if guildData[KEY_LOG_JOIN_ENABLED] and not test and channel:
                    await channel.send(
                        f":white_check_mark: ``Server Welcome:`` User {newUser.mention} "
                        f"{newUser.name}#{newUser.discriminator} "
                        f"({newUser.id}) has joined. DM sent."
                    )
                    LOGGER.info(
                        "User %s#%s (%s) has joined. DM sent.",
                        newUser.name,
                        newUser.discriminator,
                        newUser.id,
                    )

    async def sendLogUserDescription(self, user: discord.Member):
        """Sends the user's tagged description to the log channel if it exists"""
        currentGuild: discord.Guild = user.guild
        guildConfig = self.config.guild(currentGuild)

        isLogJoinEnabled = await guildConfig.get_attr(KEY_LOG_JOIN_ENABLED)()
        if not isLogJoinEnabled:
            return

        logChannelId: int = await guildConfig.get_attr(KEY_LOG_JOIN_CHANNEL)()
        logChannel: discord.TextChannel = discord.utils.get(
            currentGuild.text_channels, id=logChannelId
        )

        if not logChannel:
            return

        # check if there is a description entry for this user
        # and if so, announce it to the log join channel
        descDict: dict = await guildConfig.get_attr(KEY_DESCRIPTIONS)()
        userId = str(user.id)
        if userId in descDict:
            descText: str = descDict[userId]
            if descText:
                await logChannel.send(
                    "\n".join(
                        [
                            warning(
                                f"User {user.name}#{user.discriminator} ({user.id}) "
                                "was tagged with:"
                            ),
                            box(descText),
                        ]
                    )
                )
                LOGGER.info(
                    "User %s#%s (%s) was tagged with a description. "
                    "Posted description in the log channel.",
                    user.name,
                    user.discriminator,
                    user.id,
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
                        f":x: ``Server Leave  :`` User {leaveUser.mention} "
                        f"{leaveUser.name}#{leaveUser.discriminator} "
                        f"({leaveUser.id}) has left the server."
                    )
                LOGGER.info(
                    "User %s#%s (%s) has left the server.",
                    leaveUser.name,
                    leaveUser.discriminator,
                    leaveUser.id,
                )

    async def generateRandWelcomeImg(self, user):
        """creates an image for the specific player using their avatar and an image from the random image pool, then returns it"""
        base = Image.open(self.img_dir / random.choice(os.listdir(self.img_dir)))
        mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "MASK.png")
        )
        border_overlay = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "BORDER.png")
        )
        border_overlay_mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "data", "BORDER_mask.png")
        )
        # get avatar from User
        avatar: bytes
        session = aiohttp.ClientSession()
        # a header to successfully download user avatars for use
        used_headers = {"User-agent": "Mozilla/5.0"}

        try:
            async with session.get(str(user.avatar.url), headers=used_headers) as webp:
                avatar = await webp.read()
        except aiohttp.ClientResponseError:
            pass

        with Image.open(io.BytesIO(avatar)) as retrieved_avatar:
            if not retrieved_avatar:
                base.close()
                mask.close()
                border_overlay.close()
                border_overlay_mask.close()
                return
            else:
                retrieved_avatar = retrieved_avatar.resize((325, 325), 1)
                base.paste(border_overlay, (434, 0), border_overlay_mask)
                base.paste(retrieved_avatar, (434, 0), mask)
                generated = io.BytesIO()
                base.save(generated, format="png")
                generated.seek(0)
                base.close()
                mask.close()
                border_overlay.close()
                border_overlay_mask.close()
                return generated

    async def ensureCurrentServerHasImgCache(self, guild_id):
        """
        given a guild ID, checks if there is a folder in the image cache for the associated server. If one doesn't exist, creates it.
        """
        id_str = str(guild_id)
        try:
            os.path.join(self.img_dir, id_str).mkdir(parents=True, exist_ok=True)
        except OSError as info:
            LOGGER.info(
                "No folder for given server ID found. Created folder for server: " + id_str,
                exc_info=True,
            )
        pass

    ####################
    # MESSAGE COMMANDS #
    ####################

    # [p]welcomeset
    @commands.group(name="welcomeset")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def welcome(self, ctx: Context):
        """Server welcome message settings."""

    # [p]welcomeset dm
    @welcome.group(name="dm")
    async def dm(self, ctx: Context):
        """Server welcome DM settings.

        Upon joining the server, new members are sent a welcome DM.
        Subcommands under this command control the content and behaviors of welcome DMs.
        """

    # [p]welcomeset dm message
    @dm.command(name="message", aliases=["msg"])
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

        await self.config.guild(ctx.guild).get_attr(KEY_MESSAGE).set(message.content)
        await ctx.send("Message set to:")
        await ctx.send(f"```{message.content}```")
        LOGGER.info(
            "Message changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        LOGGER.info(message.content)

    # [p]welcomeset dm title
    @dm.command(name="title")
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

        await self.config.guild(ctx.guild).get_attr(KEY_TITLE).set(title.content)
        await ctx.send("Title set to:")
        await ctx.send(f"```{title.content}```")
        LOGGER.info(
            "Title changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        LOGGER.info(title.content)

    # [p]welcomeset dm image
    @dm.command(name="image")
    async def setImage(self, ctx: Context, imageUrl: str = None):
        """Sets an image in the embed with a URL.

        Parameters:
        -----------
        imageUrl: str (optional)
            The URL of the image to use in the DM embed. Leave blank to disable.
        """
        await self.config.guild(ctx.guild).get_attr(KEY_IMAGE).set(imageUrl)
        if imageUrl:
            await ctx.send(f"Welcome image set to `{imageUrl}`. Be sure to test it!")
        else:
            await ctx.send("Welcome image disabled.")
        LOGGER.info(
            "Image changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        LOGGER.info("Image set to %s", imageUrl)

    # [p]welcomeset dm test
    @dm.command(name="test")
    async def test(self, ctx: Context):
        """Test the welcome DM by sending a DM to you."""
        await self.sendWelcomeMessage(ctx.message.author, test=True)
        await ctx.send("If this server has been configured, you should have received a DM.")

    # [p]welcomeset dm toggle
    @dm.command(name="toggle")
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

    # [p]welcomeset greetings
    @welcome.group(name="greetings")
    async def greetings(self, ctx: Context):
        """Server greeting channel and greeting messages settings.

        Greetings are separated by pools.
        A pool can be specified as an extra argument for subcommands under this command.
        If not specified, the default pool will be used.

        Currently available greeting pools are:
        - `default`: default pool, containing greetings that are sent to new users
        - `returning`: pool of greetings that are sent to returning users
        """

    # [p]welcomeset greetings toggleimg
    @greetings.command(name="toggleimg")
    async def toggleImg(self, ctx: Context):
        """Toggles the random image on and off"""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_TOGGLE_RANDOM_MSG]:
                guildData[KEY_TOGGLE_RANDOM_MSG] = False
            elif guildData[KEY_TOGGLE_RANDOM_MSG] == False:
                # check if there is at least one image in the pool at least, otherwise tell user to add one before enabling
                if len(os.listdir(self.img_dir)) < 1:
                    await ctx.send("Add at least one image before turning the randomiser on")
                    return

                guildData[KEY_TOGGLE_RANDOM_MSG] = True

            await ctx.send(f"Sending randomised welcome image: {guildData[KEY_TOGGLE_RANDOM_MSG]}")

    # [p]welcomeset greetings add
    @greetings.command(name="add")
    async def greetAdd(self, ctx: Context, name: str, pool: Optional[str] = None):
        """Add a new greeting entry.

        If no pool is specified, the entry will be added to the default greeting pool.
        I will ask for the greeting message after you run this command.

        Including {USER} in the message will have that replaced with a ping to the new user.

        Parameters:
        -----------
        name: str
            Name of the greeting
        pool: str
            A greeting pool to add to; leave blank for the default pool
            - `default`: default pool, containing greetings that are sent to new users
            - `returning`: pool of greetings that are sent to returning users
        """

        greetingPool = GreetingPools.DEFAULT
        if pool and pool.lower() == "returning":
            greetingPool = GreetingPools.RETURNING

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

        key = KEY_GREETINGS
        if greetingPool == GreetingPools.RETURNING:
            key = KEY_RETURNING_GREETINGS

        greetings = await self.config.guild(ctx.guild).get_attr(key)()
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
        await self.config.guild(ctx.guild).get_attr(key).set(greetings)
        return

    # [p]welcomeset greetings image
    @greetings.group(name="image")
    async def image(self, ctx: Context):
        """Base command for the image command group"""
        pass

    # [p]welcomeset greetings image add
    @image.command(name="add")
    async def imgAdd(self, ctx: Context, name: str):
        """adds the attached image to the pool of random based images used to generate custom welcome images. Attaches only the first image attached.


        Additionally automatically makes the sent image conform to the dimensions and dpi that's been tested for: 72dpi, 1193x671. Mileage may vary

        """
        self.ensureCurrentServerHasImgCache(ctx.channel.guild.id)
        file_name = "{}.png"
        fp = os.path.join(self.img_dir, str(ctx.channel.guild.id), file_name.format(name))

        if os.path.exists(fp):
            await ctx.reply(
                "This name is already in use! For ease of management, please use another name."
            )
            return

        image = None
        if len(ctx.message.attachments) == 1:
            image = ctx.message.attachments[0]
            await image.save(fp)

        else:
            await ctx.reply(
                "You need to attach exactly 1 image in the message that uses this command"
            )
            return

        # Performing necessary checks to ensure that this base can produce a good generated image
        temp = Image.open(fp)
        temp_resize = temp.resize((1193, 671), 2)
        temp_resize.save(fp, dpi=(72, 72))

        # alert user that their image has been added
        await ctx.reply("Image added to this server's image cache")

    # [p]welcomeset greetings image remove
    @image.command(name="remove")
    async def imgRemove(self, ctx: Context, img_name: str):
        """Removes the specified image from the pool"""
        self.ensureCurrentServerHasImgCache(ctx.channel.guild.id)
        file_name = "{}.png"
        try:
            os.remove(
                os.path.join(self.img_dir, str(ctx.channel.guild.id), file_name.format(img_name))
            )
        except:
            await ctx.reply("the named image doesn't exist")
            return

        if len(os.listdir(os.path.join(self.img_dir, str(ctx.channel.guild.id)))) == 0:
            async with self.config.guild(ctx.guild).all() as guildData:
                guildData[KEY_TOGGLE_RANDOM_MSG] = False
            await ctx.reply("Last image deleted. Image randomiser turned off.")

        await ctx.reply("Image sucessfully removed")

    # [p]welcomeset greetings image view
    @image.command(name="view")
    async def showImg(self, ctx: Context, img_name: str):
        """shows the named image from the image pool if it exists"""
        self.ensureCurrentServerHasImgCache(ctx.channel.guild.id)
        file_name = "{}.png"
        try:
            await ctx.send(
                img_name + ":",
                file=discord.File(
                    os.path.join(
                        self.img_dir, str(ctx.channel.guild.id), file_name.format(img_name)
                    )
                ),
            )
        except:
            await ctx.reply("the named image doesn't exist")

    # [p]welcomeset greetings image list
    @image.command(name="list")
    async def listImg(self, ctx: Context):
        """Displays a list of all the images in this server's image cache"""
        self.ensureCurrentServerHasImgCache(ctx.channel.guild.id)
        listOfImages = "\n".join(os.listdir(os.path.join(self.img_dir, str(ctx.channel.guild.id))))
        if len(listOfImages) == 0:
            await ctx.reply("No images added yet.")
            return
        await ctx.reply(listOfImages.replace(".png", ""))

    # [p]welcomeset greetings channelset
    @greetings.group(name="channelset", aliases=["channelconfig", "chconfig", "chset"])
    async def greetChannelConfig(self, ctx: Context):
        """Manage server welcome channel settings."""

    # [p]welcomeset greetings channelset channel
    @greetChannelConfig.command(name="channel")
    async def greetChannelSet(self, ctx: Context, channel: discord.TextChannel = None):
        """Set the welcome channel

        Parameters:
        -----------
        channel: discord.TextChannel
            The text channel to set welcome's to. If not passed anything, will remove the welcome channel
        """
        if channel is None:
            # channel == None
            await self.config.guild(ctx.guild).get_attr(KEY_WELCOME_CHANNEL_ENABLED).set(False)
            await ctx.send("Welcome channel has been removed")
            return

        await self.config.guild(ctx.guild).get_attr(KEY_WELCOME_CHANNEL).set(channel.id)
        await self.config.guild(ctx.guild).get_attr(KEY_WELCOME_CHANNEL_ENABLED).set(True)
        await ctx.send(f"Channel set to {channel}")

        return

    # [p]welcomeset greetings channelset postfaileddm
    @greetChannelConfig.command(name="postfaileddm", aliases=["faileddm", "togglefaileddm"])
    async def greetChannelSetPostFailedDm(self, ctx: Context):
        """Toggle whether to post failed DM's to the welcome channel."""

        doPostFailedDmConfig = (
            self.config.guild(ctx.guild)
            .get_attr(KEY_WELCOME_CHANNEL_SETTINGS)
            .get_attr(KEY_POST_FAILED_DM)
        )

        doPostFailedDm = await doPostFailedDmConfig()
        await doPostFailedDmConfig.set(not doPostFailedDm)
        doPostFailedDm = await doPostFailedDmConfig()

        await ctx.send(
            info("Failed DM's will now be posted to the welcome channel.")
            if doPostFailedDm
            else info("Failed DM's will **not** be posted to the welcome channel.")
        )

    # [p]welcomeset greetings list
    @greetings.command(name="list", aliases=["ls"])
    async def greetList(self, ctx: Context, pool: Optional[str] = None):
        """List all greetings on the server.

        If no pool is specified, those from the default pool will be listed.

        Parameters:
        -----------
        pool: str
            A greeting pool to list; leave blank for the default pool
            - `default`: default pool, containing greetings that are sent to new users
            - `returning`: pool of greetings that are sent to returning users
        """

        greetingPool = GreetingPools.DEFAULT
        if pool and pool.lower() == "returning":
            greetingPool = GreetingPools.RETURNING

        key = KEY_GREETINGS
        if greetingPool == GreetingPools.RETURNING:
            key = KEY_RETURNING_GREETINGS

        greetings = await self.config.guild(ctx.guild).get_attr(key)()

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
            embed.set_footer(text=f"Pool {greetingPool.name} | Page {pageNumber}/{totalPages}")
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    # [p]welcomeset greetings remove
    @greetings.command(name="remove", aliases=["delete", "del", "rm"])
    async def greetRemove(self, ctx: Context, name: str, pool: Optional[str] = None):
        """Remove a greeting entry.

        If no pool is specified, the entry will be removed from the default greeting pool.

        Parameters:
        -----------
        name: str
            Name of the greeting to remove
        pool: str
            A greeting pool to remove from; leave blank for the default pool
            - `default`: default pool, containing greetings that are sent to new users
            - `returning`: pool of greetings that are sent to returning users
        """

        greetingPool = GreetingPools.DEFAULT
        if pool and pool.lower() == "returning":
            greetingPool = GreetingPools.RETURNING

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        key = KEY_GREETINGS
        if greetingPool == GreetingPools.RETURNING:
            key = KEY_RETURNING_GREETINGS

        greetings = await self.config.guild(ctx.guild).get_attr(key)()
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
            greetings.pop(name, None)
            await ctx.send(f"{name} removed from list")
            await self.config.guild(ctx.guild).get_attr(key).set(greetings)
        else:
            await ctx.send(f"{name} not in list of greetings")
        return

    # [p]welcomeset log
    @welcome.group(name="log")
    async def log(self, ctx: Context):
        """Server welcome logging settings.

        Members are logged when they join or leave this server.
        Subcommands under this command control the logging behavior.
        """

    # [p]welcomeset log channel
    @log.command(name="channel", aliases=["ch"])
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

    # [p]welcomeset log toggle
    @log.command(name="toggle")
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

    # [p]welcomeset tag
    @welcome.group(name="tag", aliases=["desc, description, descriptions"])
    async def tag(self, ctx: Context):
        """Manage user descriptions.

        When this user joins the server, the description associated with this user
        will be printed out to the configured logging channel.
        """

    # [p]welcomeset tag add
    @tag.command(name="add", aliases=["create", "new", "edit", "set"])
    async def addTag(self, ctx: Context, user: discord.User, *, description: str):
        """Add a description to a user.

        Parameters:
        -----------
        user: discord.User
            The user to add a description to.
        description: str
            The description to add.
        """
        userId = str(user.id)
        if len(description) > MAX_DESCRIPTION_LENGTH:
            await ctx.send(
                "The description is too long! "
                f"Max length is {MAX_DESCRIPTION_LENGTH} characters."
            )
            return

        async with self.config.guild(ctx.guild).get_attr(KEY_DESCRIPTIONS)() as descDict:
            descDict[userId] = description

        await ctx.send(
            info(f"Description set for {user.mention}."),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        LOGGER.info(
            "A welcome description has been added for %s#%s (%s)",
            user.name,
            user.discriminator,
            user.id,
        )
        LOGGER.debug(description)

    # [p]welcomeset tag get
    @tag.command(name="get", aliases=["show"])
    async def getTag(self, ctx: Context, user: discord.User):
        """Get a description for a user.

        Parameters:
        -----------
        user: discord.User
            The user to get a description for.
        """
        userId = str(user.id)
        descDict: dict = await self.config.guild(ctx.guild).get_attr(KEY_DESCRIPTIONS)()
        if userId in descDict:
            description = descDict[userId]
            if description:
                descText = "\n".join([f"**{user.mention}:**", box(description)])
                embed = discord.Embed(
                    title=f"Description for {user.name}#{user.discriminator}", description=descText
                )
                await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                return

        await ctx.send(info("No description found for that user."))

    # [p]welcomeset tag list
    @tag.command(name="list", aliases=["ls"])
    async def listTags(self, ctx: Context):
        """List all descriptions."""
        currentGuild: discord.Guild = ctx.guild
        descDict: dict = await self.config.guild(currentGuild).get_attr(KEY_DESCRIPTIONS)()
        if not descDict:
            await ctx.send(info("No descriptions have been added."))
            return
        pageList = await createTagListPages(
            descDict, embedTitle=f"Welcome descriptions for {currentGuild.name}"
        )
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    # [p]welcomeset tag remove
    @tag.command(name="remove", aliases=["delete", "del", "rm"])
    async def removeTag(self, ctx: Context, user: discord.User):
        """Remove a description from a user.

        Parameters:
        -----------
        user: discord.User
            The user to remove a description from.
        """
        userId = str(user.id)
        async with self.config.guild(ctx.guild).get_attr(KEY_DESCRIPTIONS)() as descDict:
            if userId in descDict:
                del descDict[userId]
        await ctx.send(
            info(f"Description removed for {user.mention}."),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        LOGGER.info(
            "A welcome description has been removed for %s#%s (%s)",
            user.name,
            user.discriminator,
            user.id,
        )
