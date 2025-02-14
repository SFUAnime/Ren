"""Gatekeep cog to automatically ban new users that send suspected spam as their first message."""
import logging
import os
import time
import asyncio
from datetime import datetime, timedelta, timezone
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands.context import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.chat_formatting import pagify, warning, escape
from redbot.core.bot import Red
from .constants import *
import string


class Gatekeep(commands.Cog):
    """Cog to automatically detect spam messages from accounts that meet a specific criteria.
    An account must have joined the server less than a specified amount of days ago. Only their first message will
    be checked. If their first message is deemed not spam, then they will be marked safe.
    """

    def initializeConfigAndLogger(self):
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        # Register default (empty) settings.
        self.config.register_guild(**BASE_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Gatekeep")
        if not self.logger.handlers:
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    def initializeBgTask(self):
        # On cog load, update the watchlist daily to remove accounts older than the specified amount of days
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.watchlistLoop())

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.bgTask: asyncio.Task = None
        self.config: Config = None
        self.lastChecked: datetime = None
        self.logger: logging.Logger = None

        self.initializeConfigAndLogger()
        self.initializeBgTask()

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()

    @commands.group(name="gatekeep", aliases=["gk"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _gatekeep(self, ctx: Context):
        """Automatically gatekeep accounts that post spam messages."""

    @_gatekeep.group(name="word", aliases=["w"])
    async def word(self, ctx):
        """Commands relating to words to gatekeep."""

    @_gatekeep.group(name="user", aliases=["u"])
    async def user(self, ctx):
        """Commands relating to users and the watch list."""

    @_gatekeep.command(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setChannel(self, ctx: Context, channel: discord.TextChannel = None):
        """Set the channel to log bans.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            A text channel to for logging bans.
        """

        if channel:
            await self.config.guild(ctx.guild).get_attr(KEY_LOG_CHANNEL).set(channel.id)
            self.logger.info(
                "%s#%s (%s) set the gatekeep logging channel to %s",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                channel.name,
            )
            await ctx.send(
                f":white_check_mark: **Gatekeep - Channel**: **{channel.name}** has been set "
                "as the moderation log channel!"
            )
        else:
            await self.config.guild(ctx.guild).get_attr(KEY_LOG_CHANNEL).set(None)
            await ctx.send(
                ":white_check_mark: **Gatekeep - Channel**: Moderation logs are now disabled."
            )

    @_gatekeep.command(name="threshold", aliases=["th"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setThreshold(self, ctx: Context, threshold: int):
        """Set the threshold for a message to be considered spam.

        Parameters:
        -----------
        threshold: int
            Threshold for a message to be considered spam.
        """

        if threshold > 0:
            await self.config.guild(ctx.guild).get_attr(KEY_THRESHOLD).set(threshold)
            self.logger.info(
                "%s#%s (%s) set the threshold to %s",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                str(threshold),
            )
            await ctx.send(
                f":white_check_mark: **Gatekeep - Threshold**: The threshold has been updated to **{threshold}**"
            )
        else:
            await ctx.send("The value for the threshold should be greater than 0!")

    @_gatekeep.command(name="days")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setDays(self, ctx: Context, days: int):
        """Set the number of days for an account to be cleared.

        Parameters:
        -----------
        days: int
            Number of days that an account's age must exceed to be considered 'safe'
        """

        if days > 0:
            await self.config.guild(ctx.guild).get_attr(KEY_NEW_USER_DAYS).set(days)
            self.logger.info(
                "%s#%s (%s) set the number of days to %s",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                str(days),
            )
            await ctx.send(
                f":white_check_mark: **Gatekeep - Days**: The number of days has been updated to **{days}**"
            )
        else:
            await ctx.send("The value for the days should be greater than 0!")

    @_gatekeep.command(name="activate", aliases=["enable", "on"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def activate(self, ctx: Context):
        """Activate the gatekeeping cog."""

        await self.config.guild(ctx.guild).get_attr(KEY_ACTIVE).set(True)
        await ctx.send(":warning: Gatekeeping is now active.")

    @_gatekeep.command(name="deactivate", aliases=["disable", "off"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def deactivate(self, ctx: Context):
        """Deactivate the gatekeeping cog."""

        await self.config.guild(ctx.guild).get_attr(KEY_ACTIVE).set(False)
        await ctx.send(":zzz: Gatekeeping is now inactive.")

    @_gatekeep.command(name="status", aliases=["info", "?"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def status(self, ctx: Context):
        """Show current status of the gatekeeping cog."""

        log = await self.config.guild(ctx.guild).get_attr(KEY_LOG_CHANNEL)()
        active = await self.config.guild(ctx.guild).get_attr(KEY_ACTIVE)()
        threshold = await self.config.guild(ctx.guild).get_attr(KEY_THRESHOLD)()
        nDays = await self.config.guild(ctx.guild).get_attr(KEY_NEW_USER_DAYS)()
        await ctx.send(
            ":information_source: Current Status :information_source:\n"
            f"- Log Channel: <#{log}>\n- Gatekeeping: {active}\n"
            f"- Threshold: {threshold}\n- Days to watch: {nDays}"
        )

    @_gatekeep.command(name="test", aliases=["eval", "score"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def testMsg(self, ctx: Context, *, msg: str):
        """Evaluate the score for a given message

        Parameters:
        -----------
        msg: str
            The message to evaluate the score, given that the word weights are defined.
        """
        async with self.config.guild(ctx.guild).get_attr(KEY_WORD_DICT)() as wordDict:
            # Break down into words
            words = msg.strip().split(" ")
            th = await self.config.guild(ctx.guild).get_attr(KEY_THRESHOLD)()
            score = 0
            # Begin scoring
            for word in words:
                # Remove any punctuation leftover in each word and lowercase all letters
                w = word.translate(str.maketrans("", "", string.punctuation)).lower()

                # If word is found, add to the message score
                if w in wordDict:
                    score += wordDict[w]

            if score >= th:
                judge = "this message would warrant a ban."
            else:
                judge = "this message would not warrant a ban."

            await ctx.send(
                f"This message scored {score} points. With a threshold of {th}, {judge}"
            )

    @word.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def addWord(self, ctx: Context, word: str, weight: int):
        """Add a word to the gatekeeping list.
        If the word already exists on the list,
        then update the word weight to the new weight.

        Parameters:
        -----------
        word: str
            The word to be added to the gatekeep list. This will automatically be
            converted to lowercase and have all punctuation removed. If the word
            already exists in the gatekeep list, then it will update the weight.

        weight: int
            The weight that the word has in the gatekeep list. Higher weights mean
            the word is more likely to flag the entire message as spam.
        """

        # Sanitize word by removing all punctuation
        w = word.translate(str.maketrans("", "", string.punctuation)).lower()

        # Ensure both the word is valid and the weight is greater than 0
        if len(w.split()) == 1 and weight > 0:
            async with self.config.guild(ctx.guild).get_attr(KEY_WORD_DICT)() as wordDict:
                update = False
                prev = 0
                if w in wordDict:
                    update = True
                    prev = wordDict[w]

                wordDict[w] = weight

                if update:
                    await ctx.send(f"Updated the weight of `{w}` from **{prev}** to **{weight}**.")
                else:
                    await ctx.send(f"Added the word `{w}` with a weight of **{weight}**.")

                self.logger.info(
                    "%s#%s (%s) added/updated %s with weight %s.",
                    ctx.author.name,
                    ctx.author.discriminator,
                    ctx.author.id,
                    w,
                    str(weight),
                )

        else:
            # Invalid string or the integer passed was not a positive value
            await ctx.send(
                "The word is invalid and/or the value for the weight should be greater than 0!"
            )

    @word.command(name="remove", aliases=["delete", "del", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def removeWord(self, ctx: Context, word: str):
        """Remove a word from the gatekeeping list, if it exists.

        Parameters:
        -----------
        word: str
            The word to be removed to the gatekeep list. This will automatically be
            converted to lowercase and have all punctuation removed.
        """

        # Sanitize word by removing all punctuation
        w = word.translate(str.maketrans("", "", string.punctuation)).lower()

        # Ensure the word is valid
        if len(w.split()) == 1:
            async with self.config.guild(ctx.guild).get_attr(KEY_WORD_DICT)() as wordDict:
                # Pop removes the item with key 'w' from the dictionary if it exists. Othewise it returns None
                if wordDict.pop(w, None):
                    await ctx.send(f"Removed `{w}` from the list.")
                    self.logger.info(
                        "%s#%s (%s) removed %s.",
                        ctx.author.name,
                        ctx.author.discriminator,
                        ctx.author.id,
                        w,
                    )
                else:
                    await ctx.send(f"`{w}` is not in the list.")

        else:
            # Invalid string passed
            await ctx.send("The word should be a non-empty string!")

    @word.command(name="list", aliases=["ls", "words"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def listWords(self, ctx: Context):
        """Lists the words on the word list for the server."""

        display = []  # List of text for paginator to use.  Will be constructed from KEY_WORD_DICT.

        # Loop through the word dictionary object
        wordDict = await self.config.guild(ctx.guild).get_attr(KEY_WORD_DICT)()
        for word, weight in wordDict.items():
            # Construct the display list
            text = f"{word}: {weight}"
            display.append(text)

        # Check if the display list is empty
        if not display:
            await ctx.send("The word list is empty.")
            return

        pageList = []
        msg = "\n".join(display)
        pages = list(pagify(msg, page_length=200))
        totalPages = len(pages)
        async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
            embed = discord.Embed(
                title=f"List of words to gatekeep in **{ctx.guild.name}**", description=page
            )
            embed.set_footer(text=f"Page {pageNumber}/{totalPages}")
            embed.colour = discord.Colour.red()
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    @user.command(name="initialize", aliases=["init"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def initWatchList(self, ctx: Context):
        """Initialize the list of user IDs to place on the watchlist.
        Users that joined the server for less than X days will be placed on the watchlist. (X is configurable)
        """

        def check(msg: discord.Message):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Get confirmation before initializing. It loops through every member in a server, so it could take a while
        await ctx.send(warning("This operation may take a while. Type 'yes' to confirm."))
        try:
            response = await self.bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("No response after 30 seconds, this operation will not be executed.")
            return

        if response.content.lower() != "yes":
            await ctx.send("This operation will not be executed.")
            return

        # Confirmed, so initialization process begins
        start = time.time()
        current = datetime.now(timezone.utc)
        nDays = await self.config.guild(ctx.guild).get_attr(KEY_NEW_USER_DAYS)()
        watchList = []
        for member in ctx.guild.members:
            # If a member has been in the server for less than X days, then they get added to the watch list (X is configurable)
            if (
                current - member.joined_at < timedelta(days=nDays)
                and not member.guild_permissions.administrator
                and not await self.bot.is_automod_immune(member)
            ):
                watchList.append(int(member.id))
                self.logger.info(
                    "%s#%s (%s) added to the watch list.",
                    member.name,
                    member.discriminator,
                    member.id,
                )
        await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST).set(watchList)

        end = time.time() - start
        await ctx.send(f"Operation took {end:.3f} seconds.")

    @user.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def addUser(self, ctx: Context, user: discord.User):
        """Add a user to the watch list.

        Parameters:
        -----------
        user: User
            The user to be added to the watch list. This can be their username or ID.
        """

        watchList = await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST)()
        if user.id not in watchList:
            watchList.append(int(user.id))
            await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST).set(watchList)
            await ctx.send(f"Added user ID `{user.id}` to the watch list.")

            self.logger.info(
                "%s#%s (%s) added user ID %s to the watch list for %s.",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                user.id,
                ctx.guild.name,
                )
        else:
            await ctx.send(f"User ID `{user.id}` is already in the watch list.")

    @user.command(name="remove", aliases=["delete", "del", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def removeUser(self, ctx: Context, user: discord.User):
        """Remove a user from the watch list.

        Parameters:
        -----------
        user: User
            The user to be removed from the watch list. This can be their username or ID.
        """

        watchList = await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST)()
        if user.id in watchList:
            watchList.remove(user.id)
            await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST).set(watchList)
            await ctx.send(f"Removed user ID `{user.id}` to the watch list.")

            self.logger.info(
                "%s#%s (%s) removed user ID %s from the watch list for %s.",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                user.id,
                ctx.guild.name,
            )
        else:
            await ctx.send(f"User ID `{user.id}` is not in the watch list.")

    @user.command(name="list", aliases=["ls", "users"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def listWatch(self, ctx: Context):
        """Lists the users on the watch list for the server."""

        display = (
            []
        )  # List of text for paginator to use.  Will be constructed from KEY_WATCH_LIST.

        # Loop through the watch list
        watchList = await self.config.guild(ctx.guild).get_attr(KEY_WATCH_LIST)()
        for id in watchList:
            # Construct the display list
            member = discord.utils.get(ctx.guild.members, id=int(id))
            if member:
                text = f"{member.name}#{member.discriminator} ({member.id})"
                display.append(text)
            else:
                text = f"Unknown User ({id})"
                display.append(text)

        # Check if the display list is empty
        if not display:
            await ctx.send("The watch list is empty.")
            return

        pageList = []
        msg = "\n".join(display)
        pages = list(pagify(msg, page_length=300))
        totalPages = len(pages)
        async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
            embed = discord.Embed(
                title=f"List of users to watch in **{ctx.guild.name}**", description=page
            )
            embed.set_footer(text=f"Page {pageNumber}/{totalPages}")
            embed.colour = discord.Colour.red()
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    async def watchlistLoop(self):
        """Daily update loop to keep the watchlist small."""
        self.logger.info("Waiting for bot to be ready")
        await self.bot.wait_until_red_ready()
        self.logger.info("Bot is ready")
        while self == self.bot.get_cog("Gatekeep"):
            if self.lastChecked.day != datetime.now().day:
                self.lastChecked = datetime.now()
                await self.checkWatchlist()
            await asyncio.sleep(60)  # pylint: disable=no-member

    async def checkWatchlist(self):
        """Check watch list once."""
        guilds = self.bot.guilds
        current = datetime.now(timezone.utc)
        for guild in guilds:
            watchList = await self.config.guild(guild).get_attr(KEY_WATCH_LIST)()
            wl = await self.config.guild(guild).get_attr(KEY_WATCH_LIST)()
            nDays = await self.config.guild(guild).get_attr(KEY_NEW_USER_DAYS)()
            for id in watchList:
                member = discord.utils.get(guild.members, id=id)
                if member:
                    # Remove member from watch list if they have been in the server for over the required amount of days
                    if (
                        current - member.joined_at > timedelta(days=nDays)
                        or member.guild_permissions.administrator
                        or await self.bot.is_automod_immune(member)
                    ):
                        wl.remove(int(id))
                        self.logger.info(
                            "%s#%s (%s) removed from the watch list. (Trusted user)",
                            member.name,
                            member.discriminator,
                            member.id,
                        )
                else:
                    # Remove member if they are no longer in the server (can't log because of it being an id)
                    wl.remove(int(id))
                    self.logger.info(
                        "Member with id (%s) removed from the watch list. (Not in server)", id
                    )

            await self.config.guild(guild).get_attr(KEY_WATCH_LIST).set(wl)
            self.logger.info("Refreshed the watch list for %s", guild.name)

    # The async function that is triggered on new member join.
    @commands.Cog.listener()
    async def on_member_join(self, newMember: discord.Member):
        # Add member to list, if they joined and aren't already on the list
        watchList = await self.config.guild(newMember.guild).get_attr(KEY_WATCH_LIST)()
        if int(newMember.id) not in watchList:
            watchList.append(int(newMember.id))
            self.logger.info(
                "%s#%s (%s) added to the watch list.",
                newMember.name,
                newMember.discriminator,
                newMember.id,
            )
            await self.config.guild(newMember.guild).get_attr(KEY_WATCH_LIST).set(watchList)

    # The async function that is triggered on any message being sent.
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # General checks for doing nothing when a message is sent
        if message.guild is None:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        # Author has the 'Administrator' permissions OR they have a role that is granted immunity in the server's config
        if message.author.guild_permissions.administrator or await self.bot.is_automod_immune(
            message
        ):
            return

        # Cog handles message checking from here on out

        # Do nothing if inactive
        if not await self.config.guild(message.guild).get_attr(KEY_ACTIVE)():
            return

        # Check the list
        watchList = await self.config.guild(message.guild).get_attr(KEY_WATCH_LIST)()
        # Do nothing if the message author is not on the watch list to begin with
        if int(author.id) not in watchList:
            return

        # Evaluation of the message contents happen here
        async with self.config.guild(message.guild).get_attr(KEY_WORD_DICT)() as wordDict:
            # Break down into words
            words = message.content.strip().split(" ")
            th = await self.config.guild(message.guild).get_attr(KEY_THRESHOLD)()

            score = 0
            # Begin scoring
            for word in words:
                # Remove any punctuation leftover in each word and lowercase all letters
                w = word.translate(str.maketrans("", "", string.punctuation)).lower()

                # If word is found, add to the message score
                if w in wordDict:
                    score += wordDict[w]

            # Determine if spam
            if score >= th:
                # Proceed to ban and announce to mod log channel
                await message.author.ban(
                    delete_message_seconds=604800,
                    reason="Message was flagged as spam by Ren's gatekeep cog.",
                )

                ch = await self.config.guild(message.guild).get_attr(KEY_LOG_CHANNEL)()
                m = (
                    message.content
                    if len(message.content) < 300
                    else message.content[:300] + "..."
                )
                await self.bot.get_channel(ch).send(
                    f"Banned {author.mention} `{author.id}` for posting spam. The message score was {score}, "
                    f"which exceeded the threshold of {th}. Their message was:```\n{escape(m, formatting=True)}\n```"
                )

                self.logger.info(
                    "%s#%s (%s) was banned from %s for spam. Message score was %s, which exceed threshold of %s.",
                    author.name,
                    author.discriminator,
                    author.id,
                    message.guild.name,
                    str(score),
                    str(th),
                )

            # Remove the author from the watch list. Ban = gone from server, no ban = they're probably not a bot
            watchList.remove(int(author.id))
            await self.config.guild(author.guild).get_attr(KEY_WATCH_LIST).set(watchList)
