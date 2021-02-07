"""Highlights cog: DM a user certain "highlight" words that they specify.

Credit: This idea was first implemented by Danny (https://github.com/Rapptz/) but at
the time, that bot was closed source.
"""
from datetime import timedelta, timezone
import logging
import re
from threading import Lock
import asyncio
import aiohttp
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils import chat_formatting, paginator

DEFAULT_TIMEOUT = 20
DELETE_TIME = 5
MAX_WORDS_HIGHLIGHT = 20
MAX_WORDS_IGNORE = 20
KEY_BLACKLIST = "blacklist"
KEY_TIMEOUT = "timeout"
KEY_WORDS = "words"
KEY_WORDS_IGNORE = "ignoreWords"
KEY_IGNORE = "ignoreChannelID"

BASE_GUILD_MEMBER = {
    KEY_BLACKLIST: [],
    KEY_TIMEOUT: DEFAULT_TIMEOUT,
    KEY_WORDS: [],
    KEY_WORDS_IGNORE: [],
}

BASE_GUILD = {
    KEY_IGNORE: None,
    "denylistChannels": [],
}


class Highlight(commands.Cog):
    """Slack-like feature to be notified based on specific words."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.lock = Lock()
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_member(**BASE_GUILD_MEMBER)
        self.config.register_guild(**BASE_GUILD)

        self.lastTriggered = {}
        self.triggeredLock = Lock()
        self.wordFilter = None

        # Initialize logger and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Highlight")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename=str(saveFolder) + "/info.log", encoding="utf-8", mode="a"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    async def _sleepThenDelete(self, msg, time):
        await asyncio.sleep(time)  # pylint: disable=no-member
        await msg.delete()

    def _registerUser(self, guildId, userId):
        """Checks to see if user is registered, and if not, registers the user.
        If the user is already registered, this method will do nothing. If the
        user is not, they will be initialized to contain an empty words list.

        Parameters:
        -----------
        guildId: int
            The guild ID for the user.
        userId: int
            The user ID.

        Returns:
        --------
            None.
        """
        if guildId not in self.highlights.keys():
            self.highlights[guildId] = {}

        if userId not in self.highlights[guildId].keys():
            self.highlights[guildId][userId] = {
                KEY_WORDS: [],
                KEY_BLACKLIST: [],
                KEY_TIMEOUT: DEFAULT_TIMEOUT,
            }
            return

        if KEY_BLACKLIST not in self.highlights[guildId][userId].keys():
            self.highlights[guildId][userId][KEY_BLACKLIST] = []

        if KEY_TIMEOUT not in self.highlights[guildId][userId].keys():
            self.highlights[guildId][userId][KEY_TIMEOUT] = DEFAULT_TIMEOUT

    @commands.group(name="highlight", aliases=["hl"])
    @commands.guild_only()
    async def highlight(self, ctx):
        """Slack-like feature to be notified based on specific words outside of
        at-mentions."""

    @highlight.group(name="guild")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def guildSettings(self, ctx: Context):
        """Guild-wide settings"""

    @guildSettings.group(name="channel", aliases=["ch"])
    async def guildChannels(self, ctx: Context):
        """Channel denylist.

        Channels on this list will NOT trigger user highlights.
        """

    @guildChannels.command(name="show", aliases=["ls"])
    async def guildChannelsDenyList(self, ctx: Context):
        """List the channels in the denylist."""
        dlChannels = await self.config.guild(ctx.guild).denylistChannels()

        if dlChannels:
            page = paginator.Pages(ctx=ctx, entries=dlChannels, show_entry_count=True)
            page.embed.title = "Denylist channels for: **{}**".format(ctx.guild.name)
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await ctx.send(f"There are no channels on the denylist for **{ctx.guild.name}**!")

    @guildChannels.command(name="add")
    async def guildChannelsDenyAdd(self, ctx: Context, channelName: str):
        """Add a channel to the denylist.

        Channels in this list will NOT trigger user highlights.

        Parameters:
        -----------
        channelName: str
            The channel name you wish to not trigger user highlights for.
        """
        async with self.config.guild(ctx.guild).denylistChannels() as dlChannels:
            if channelName in dlChannels:
                await ctx.send(f"**{channelName}** is already on the denylist.")
            else:
                dlChannels.append(channelName)
                await ctx.send(
                    f"Messages in **{channelName}** will no longer trigger highlights for users"
                )

    @guildChannels.command(name="del", aliases=["delete", "remove", "rm"])
    async def guildChannelsDenyDelete(self, ctx: Context, channelName: str):
        """Remove a channel from the denylist.

        Parameters:
        -----------
        channelName: str
            The channel name you wish to remove from the denylist.
        """
        async with self.config.guild(ctx.guild).denylistChannels() as dlChannels:
            if channelName in dlChannels:
                dlChannels.remove(channelName)
                await ctx.send(f"**{channelName}** removed from the denylist.")
            else:
                await ctx.send(f"**{channelName}** is not on the denylist.")

    @highlight.command(name="add")
    @commands.guild_only()
    async def addHighlight(self, ctx, *, word: str):
        """Add a word to be highlighted in the current guild."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if len(userWords) < MAX_WORDS_HIGHLIGHT and word not in userWords:
                # user can only have MAX_WORDS_HIGHLIGHT words
                userWords.append(word)
                await ctx.send(
                    "Highlight word added, {}".format(userName), delete_after=DELETE_TIME
                )
            else:
                await ctx.send(
                    "Sorry {}, you already have {} words highlighted, or you "
                    "are trying to add a duplicate word".format(userName, MAX_WORDS_HIGHLIGHT),
                    delete_after=DELETE_TIME,
                )
        await ctx.message.delete()

    @highlight.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    async def removeHighlight(self, ctx, *, word: str):
        """Remove a highlighted word in the current guild."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if word in userWords:
                userWords.remove(word)
                await ctx.send(
                    "Highlight word removed, {}".format(userName), delete_after=DELETE_TIME
                )
            else:
                await ctx.send(
                    "Sorry {}, you don't have this word " "highlighted".format(userName),
                    delete_after=DELETE_TIME,
                )
        await ctx.message.delete()

    @highlight.command(name="list", aliases=["ls"])
    @commands.guild_only()
    async def listHighlight(self, ctx: Context):
        """List your highighted words for the current guild."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if userWords:
                msg = ""
                for word in userWords:
                    msg += "{}\n".format(word)

                embed = discord.Embed(description=msg, colour=discord.Colour.red())
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url
                )
                try:
                    await ctx.message.author.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send(
                        "{}, you do not have DMs enabled, please enable them!".format(
                            ctx.message.author.mention
                        ),
                        delete_after=DELETE_TIME,
                    )
                else:
                    await ctx.send("Please check your DMs.", delete_after=DELETE_TIME)
            else:
                await ctx.send(
                    "Sorry {}, you have no highlighted words " "currently".format(userName),
                    delete_after=DELETE_TIME,
                )

    @highlight.group(name="blacklist", aliases=["bl"])
    @commands.guild_only()
    async def userBlacklist(self, ctx: Context):
        """Blacklist certain users from triggering your words."""

    @userBlacklist.command(name="add")
    @commands.guild_only()
    async def userBlAdd(self, ctx: Context, user: discord.Member):
        """Add a user to your blacklist.

        Parameters:
        -----------
        user: discord.Member
            The user you wish to block from triggering your highlight words.
        """
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).blacklist() as userBl:
            if user.id not in userBl:
                userBl.append(user.id)
                await ctx.send(
                    "{} added to the blacklist, {}".format(user.name, userName),
                    delete_after=DELETE_TIME,
                )
            else:
                await ctx.send("This user is already on the blacklist!", delete_after=DELETE_TIME)
        await ctx.message.delete()

    @userBlacklist.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    async def userBlRemove(self, ctx: Context, user: discord.Member):
        """Remove a user from your blacklist.

        Parameters:
        -----------
        user: discord.Member
            The user you wish to remove from your blacklist.
        """
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).blacklist() as userBl:
            if user.id in userBl:
                userBl.remove(user.id)
                await ctx.send(
                    "{} removed from blacklist, {}".format(user.name, userName),
                    delete_after=DELETE_TIME,
                )
            else:
                await ctx.send("This user is not on the blacklist!", delete_after=DELETE_TIME)
        await ctx.message.delete()

    @userBlacklist.command(name="clear", aliases=["cls"])
    @commands.guild_only()
    async def userBlClear(self, ctx: Context):
        """Clear your user blacklist.

        Will ask for confirmation.
        """
        await ctx.send(
            "Are you sure you want to clear your blacklist?  Type "
            "`yes` to continue, otherwise type something else."
        )

        def check(msg):
            return msg.author == ctx.message.author and msg.channel == ctx.message.channel

        try:
            response = await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            pass
        else:
            if response.content.lower() == "yes":
                async with self.config.member(ctx.author).blacklist() as userBl:
                    userBl.clear()
                await ctx.send("Your highlight blacklist was cleared.")
                return
        await ctx.send("Not clearing your blacklist.")

    @userBlacklist.command(name="list", aliases=["ls"])
    @commands.guild_only()
    async def userBlList(self, ctx: Context):
        """List the users on your blacklist."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).blacklist() as userBl:
            if userBl:
                msg = ""
                for userId in userBl:
                    userObj = discord.utils.get(ctx.message.guild.members, id=userId)
                    if not userObj:
                        continue
                    msg += "{}\n".format(userObj.name)
                if msg == "":
                    msg = "You have blacklisted users that are no longer in the guild."

                embed = discord.Embed(description=msg, colour=discord.Colour.red())
                embed.title = "Blacklisted users on {}".format(ctx.message.guild.name)
                embed.set_author(name=userName, icon_url=ctx.message.author.avatar_url)
                try:
                    await ctx.message.author.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send(
                        "{}, you do not have DMs enabled, please enable them!".format(
                            ctx.message.author.mention
                        ),
                        delete_after=DELETE_TIME,
                    )
                else:
                    await ctx.send("Please check your DMs.", delete_after=DELETE_TIME)
            else:
                await ctx.send(
                    "Sorry {}, you have no backlisted users " "currently".format(userName),
                    delete_after=DELETE_TIME,
                )

    @highlight.group(name="ignore")
    @commands.guild_only()
    async def wordIgnore(self, ctx: Context):
        """Ignore certain words to avoid having them trigger your DMs.

        Suppose you have a word X in your highlighted words, and a word Y you are
        ignoring.  Then, we have some scenarios as below:
        - "X something something": triggers DM.
        - "X Y": does NOT triggers DM.
        - "X something something Y": does NOT trigger DM.
        """

    @wordIgnore.command(name="add")
    @commands.guild_only()
    async def wordIgnoreAdd(self, ctx: Context, *, word: str):
        """Add words to your ignore list.

        Parameters:
        -----------
        word: str
            The word you wish to ignore.
        """
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).ignoreWords() as ignoreWords:
            if len(ignoreWords) < MAX_WORDS_IGNORE and word not in ignoreWords:
                ignoreWords.append(word)
                await ctx.send(
                    "{} added to the ignore list, {}".format(word, userName),
                    delete_after=DELETE_TIME,
                )
            else:
                await ctx.send(
                    "Sorry {}, you are already ignoring {} words, or you are "
                    "trying to add a duplicate word".format(userName, MAX_WORDS_IGNORE),
                    delete_after=DELETE_TIME,
                )
        await ctx.message.delete()

    @wordIgnore.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    async def wordIgnoreRemove(self, ctx: Context, *, word: str):
        """Remove an ignored word from the list."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).ignoreWords() as ignoreWords:
            if word in ignoreWords:
                ignoreWords.remove(word)
                await ctx.send(
                    "{} removed from the ignore list, {}".format(word, userName),
                    delete_after=DELETE_TIME,
                )
            else:
                await ctx.send(
                    "You are not currently ignoring this word!", delete_after=DELETE_TIME
                )
        await ctx.message.delete()

    @wordIgnore.command(name="list", aliases=["ls"])
    @commands.guild_only()
    async def wordIgnoreList(self, ctx: Context):
        """List ignored words."""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).ignoreWords() as userWords:
            if userWords:
                msg = ""
                for word in userWords:
                    msg += "{}\n".format(word)

                embed = discord.Embed(description=msg, colour=discord.Colour.red())
                embed.set_author(
                    name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url
                )
                try:
                    await ctx.message.author.send(embed=embed)
                except discord.Forbidden:
                    await ctx.send(
                        "{}, you do not have DMs enabled, please enable them!".format(
                            ctx.message.author.mention
                        ),
                        delete_after=DELETE_TIME,
                    )
                else:
                    await ctx.send("Please check your DMs.")
            else:
                await ctx.send(
                    "Sorry {}, you currently do not have any ignored " "words.".format(userName),
                    delete_after=DELETE_TIME,
                )

    @highlight.command(name="timeout")
    @commands.guild_only()
    async def setTimeout(self, ctx: Context, seconds: int):
        """Set the timeout between consecutive highlight triggers.

        This applies to consecutive highlights within the same channel.
        If your words are triggered within this timeout period, you will
        only be notified once.

        Parameters:
        -----------
        seconds: int
            The timeout between consecutive triggers within a channel, in seconds.
            Minimum timeout is 0 (always trigger).
            Maximum timeout is 3600 seconds (1 hour).
        """
        if seconds < 0 or seconds > 3600:
            await ctx.send("Please specify a timeout between 0 and 3600 seconds!")
            return

        await self.config.member(ctx.author).timeout.set(seconds)

        await ctx.send("Timeout set to {} seconds.".format(seconds), delete_after=DELETE_TIME)
        await ctx.message.delete()

    def _triggeredRecently(self, msg, uid, timeout=DEFAULT_TIMEOUT):
        """See if a user has been recently triggered.

        Parameters:
        -----------
        msg: discord.Message
            The message that we wish to check the time, guild ID, and channel ID
            against.
        uid: int
            The user ID of the user we want to check.
        timeout: int
            The user timeout, in seconds.

        Returns:
        --------
        bool
            True if the user has been triggered recently in the specific channel.
            False if the user has not been triggered recently.
        """
        sid = msg.guild.id
        cid = msg.channel.id

        if sid not in self.lastTriggered.keys():
            return False
        if cid not in self.lastTriggered[sid].keys():
            return False
        if uid not in self.lastTriggered[sid][cid].keys():
            return False

        timeoutVal = timedelta(seconds=timeout)
        lastTrig = self.lastTriggered[sid][cid][uid]
        self.logger.debug(
            "Timeout %s, last triggered %s, message timestamp %s",
            timeoutVal,
            lastTrig,
            msg.created_at,
        )
        if msg.created_at - lastTrig < timeoutVal:
            # User has been triggered recently.
            return True
        # User hasn't been triggered recently, so we can trigger them, if
        # applicable.
        return False

    def _triggeredUpdate(self, msg, uid):
        """Updates the last time a user had their words triggered in a channel.

        Parameters:
        -----------
        msg: discord.Message
            The message that triggered an update for a user.  Should contain the
            timestamp, guild ID, and channel ID to update.
        uid: int
            The user ID of the user we want to update.

        Returns:
        --------
        None, updates self.lastTriggered[sid][cid][uid] with the newest datetime.
        """
        sid = msg.guild.id
        cid = msg.channel.id

        with self.triggeredLock:
            if sid not in self.lastTriggered.keys():
                self.lastTriggered[sid] = {}
            if cid not in self.lastTriggered[sid].keys():
                self.lastTriggered[sid][cid] = {}
            self.lastTriggered[sid][cid][uid] = msg.created_at

    async def checkHighlights(self, msg: discord.Message):
        """Background listener to check if a highlight has been triggered."""
        if not isinstance(msg.channel, discord.TextChannel):
            return

        user = msg.author

        # Prevent bots from triggering your highlight word.
        if user.bot:
            return

        # Prevent messages in a denylist channel from triggering highlight words
        if msg.channel.name in await self.config.guild(msg.channel.guild).denylistChannels():
            self.logger.debug("Message is from a denylist channel, returning")
            return

        # Don't send notification for filtered messages
        if not self.wordFilter:
            self.wordFilter = self.bot.get_cog("WordFilter")
        elif await self.wordFilter.containsFilterableWords(msg):
            return

        tasks = []

        activeMessages = []
        try:
            async for message in msg.channel.history(limit=50, before=msg):
                activeMessages.append(message)
        except (aiohttp.ClientResponseError, aiohttp.ServerDisconnectedError):
            self.logger.error("Error within discord.py!", exc_info=True)

        # Iterate through every user's words on the guild, and notify all highlights
        guildData = await self.config.all_members(msg.guild)
        for currentUserId, data in guildData.items():
            self.logger.debug("User ID: %s", currentUserId)
            isWordIgnored = False

            # Handle case where user was at-mentioned.
            if currentUserId in [atMention.id for atMention in msg.mentions]:
                continue

            # Handle case where message author has been blacklisted by the user.
            if KEY_BLACKLIST in data.keys() and msg.author.id in data[KEY_BLACKLIST]:
                continue

            # Handle case where message contains words being ignored byu the user.
            if KEY_WORDS_IGNORE in data.keys():
                self.logger.debug("Checking for ignored words")
                for word in data[KEY_WORDS_IGNORE]:
                    if self._isWordMatch(word, msg.content):
                        self.logger.debug("%s is being ignored, skipping user.", word)
                        isWordIgnored = True
                        break

            if isWordIgnored:
                continue

            # If we reach this point, then the message is not from a user that has been
            # blacklisted, nor does the message contain any ignored words, so now we can
            # check to see if there is anything that needs to be highlighted.
            for word in data[KEY_WORDS]:
                active = _isActive(currentUserId, msg, activeMessages)
                match = self._isWordMatch(word, msg.content)
                timeout = data[KEY_TIMEOUT] if KEY_TIMEOUT in data.keys() else DEFAULT_TIMEOUT
                triggeredRecently = self._triggeredRecently(msg, currentUserId, timeout)
                if match and not active and not triggeredRecently and user.id != currentUserId:
                    hiliteUser = msg.guild.get_member(currentUserId)
                    if not hiliteUser:
                        # Handle case where user is no longer in the guild of interest.
                        continue
                    perms = msg.channel.permissions_for(hiliteUser)
                    if not perms.read_messages:
                        # Handle case where user cannot see the channel.
                        break
                    self._triggeredUpdate(msg, currentUserId)
                    tasks.append(self._notifyUser(hiliteUser, msg, word))

        await asyncio.gather(*tasks)  # pylint: disable=no-member

    async def _notifyUser(self, user: discord.Member, message: discord.Message, word: str):
        """Notify the user of the triggered highlight word."""
        msgs = []
        try:
            async for msg in message.channel.history(limit=6, around=message):
                msgs.append(msg)
        except aiohttp.ClientResponseError as error:
            self.logger.error("Client response error within discord.py!", exc_info=True)
            self.logger.error(error)
        except aiohttp.ServerDisconnectedError as error:
            self.logger.error("Server disconnect error within discord.py!", exc_info=True)
            self.logger.error(error)
        msgContext = sorted(msgs, key=lambda r: r.created_at)
        msgUrl = message.jump_url
        notifyMsg = (
            "In #{1.channel.name}, you were mentioned with highlight word "
            "**{0}**:".format(word, message)
        )
        embedMsg = ""
        msgStillThere = False
        for msg in msgContext:
            time = msg.created_at
            time = time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime("%H:%M:%S %Z")
            escapedMsg = chat_formatting.escape(msg.content, formatting=True)
            # If message contains spoilers, then the bot will replace the message
            # with <<spoilers>>
            if len(escapedMsg.split("\\|\\|")) > 2:
                escapedMsg = "<<spoilers>>"
            embedMsg += "[{0}] {1.author.name}#{1.author.discriminator}: {2}" "\n".format(
                time, msg, escapedMsg
            )
            if self._isWordMatch(word, msg.content):
                msgStillThere = True
        if not msgStillThere:
            return
        embed = discord.Embed(title=user.name, description=embedMsg, colour=discord.Colour.red())
        embed.add_field(name="Context", value="[Click to Jump]({})".format(msgUrl))
        time = message.created_at.replace(tzinfo=timezone.utc).astimezone(tz=None)
        footer = "Triggered at | {}".format(time.strftime("%a, %d %b %Y %I:%M%p %Z"))
        embed.set_footer(text=footer)
        try:
            await user.send(content=notifyMsg, embed=embed)
            self.logger.info(
                "%s#%s (%s) was successfully triggered.", user.name, user.discriminator, user.id
            )
        except discord.errors.Forbidden as error:
            self.logger.error(
                "Could not notify %s#%s (%s)!  They probably has DMs disabled!",
                user.name,
                user.discriminator,
                user.id,
            )

    # Event listeners
    @commands.Cog.listener("on_message")
    async def onMessage(self, msg):
        """Background listener to check messages for highlight DMs."""
        await self.checkHighlights(msg)

    def _isWordMatch(self, word, string):
        """See if the word/regex matches anything in string.

        Parameters:
        -----------
        word: str
            The regex/word you wish to see exists.
        string: str
            The string in which you want to check if word is in.

        Returns:
        --------
        bool
            Whether or not word is in string.
        """
        try:
            regex = r"\b{}\b".format(re.escape(word.lower()))
            return bool(re.search(regex, string.lower()))
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error("Regex error: %s", word)
            self.logger.error(error)
            return False


def _isActive(userId, originalMessage, messages, timeout=DEFAULT_TIMEOUT):
    """Checks to see if the user has been active on a channel, given a message.

    Parameters:
    -----------
    userId: int
        The user ID we wish to check.
    originalMessage: discord.Message
        The original message whose base timestamp we wish to check against.
    messages: [ discord.Message ]
        A list of discord message objects that we wish to check the user against.
    timeout: int
        The amount of time to ignore, in seconds. The difference in time between
        the user's last message and the current message must be GREATER THAN this
        to be considered "active".

    Returns:
    --------
    bool
        True, if the user has spoken timeout seconds before originalMessage.
        False, otherwise.
    """
    for msg in messages:
        deltaSinceMsg = originalMessage.created_at - msg.created_at
        if msg.author.id == userId and deltaSinceMsg <= timedelta(seconds=timeout):
            return True
    return False
