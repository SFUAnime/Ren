"""Highlights cog: DM a user certain "highlight" words that they specify.

Credit: This idea was first implemented by Danny (https://github.com/Rapptz/) but at
the time, that bot was closed source.
"""
from copy import deepcopy
from datetime import timedelta, timezone
import logging
import os
import re
from threading import Lock
import asyncio
import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils import chat_formatting

DEFAULT_TIMEOUT = 20
MAX_WORDS = 20
KEY_BLACKLIST = "blacklist"
KEY_TIMEOUT = "timeout"
KEY_WORDS = "words"
KEY_IGNORE = "ignoreChannelID"

BASE_GUILD_MEMBER = \
{
 KEY_BLACKLIST: [],
 KEY_TIMEOUT: DEFAULT_TIMEOUT,
 KEY_WORDS: []
}

BASE_GUILD = \
{
 KEY_IGNORE: None
}

class Highlight(commands.Cog):
    """Slack-like feature to be notified based on specific words."""
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.lock = Lock()
        self.config = Config.get_conf(self, identifier=5842647)
        self.config.register_member(**BASE_GUILD_MEMBER)
        self.config.register_guild(**BASE_GUILD)

        self.lastTriggered = {}
        self.triggeredLock = Lock()
        self.wordFilter = None
        self.logger = None

    async def _sleepThenDelete(self, msg, time):
        await asyncio.sleep(time) # pylint: disable=no-member
        await msg.delete()

    def _registerUser(self, guildId, userId):
        """Checks to see if user is registered, and if not, registers the user.
        If the user is already registered, this method will do nothing.
        If the user is not, they will be initialized to contain an empty words list.

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
            self.highlights[guildId][userId] = {KEY_WORDS: [], KEY_BLACKLIST: [],
                                                KEY_TIMEOUT: DEFAULT_TIMEOUT}
            return

        if KEY_BLACKLIST not in self.highlights[guildId][userId].keys():
            self.highlights[guildId][userId][KEY_BLACKLIST] = []

        if KEY_TIMEOUT not in self.highlights[guildId][userId].keys():
            self.highlights[guildId][userId][KEY_TIMEOUT] = DEFAULT_TIMEOUT

    @commands.group(name="highlight", aliases=["hl"])
    @commands.guild_only()
    async def highlight(self, ctx):
        """Slack-like feature to be notified based on specific words outside of at-mentions"""

    @highlight.command(name="add")
    @commands.guild_only()
    async def addHighlight(self, ctx, *, word: str):
        """Add a word to be highlighted in the current guild"""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if len(userWords) < MAX_WORDS and word not in userWords:
                # user can only have MAX_WORDS words
                userWords.append(word)
                confMsg = await ctx.send("Highlight word added, {}".format(userName))
            else:
                confMsg = await ctx.send("Sorry {}, you already have {} words "
                                         "highlighted, or you are trying to add "
                                         "a duplicate word".format(userName,
                                                                   MAX_WORDS))
        await ctx.message.delete()
        await self._sleepThenDelete(confMsg, 5)

    @highlight.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    async def removeHighlight(self, ctx, *, word: str):
        """Remove a highlighted word in the current guild"""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if word in userWords:
                userWords.remove(word)
                confMsg = await ctx.send("Highlight word removed, {}".format(userName))
            else:
                confMsg = await ctx.send("Sorry {}, you don't have this word "
                                         "highlighted".format(userName))
        await ctx.message.delete()
        await self._sleepThenDelete(confMsg, 5)

    @highlight.command(name="list", aliases=["ls"])
    @commands.guild_only()
    async def listHighlight(self, ctx: Context):
        """List your highighted words for the current guild"""
        userName = ctx.message.author.name

        async with self.config.member(ctx.author).words() as userWords:
            if userWords:
                msg = ""
                for word in userWords:
                    msg += "{}\n".format(word)

                embed = discord.Embed(description=msg,
                                      colour=discord.Colour.red())
                embed.set_author(name=ctx.message.author.name,
                                 icon_url=ctx.message.author.avatar_url)
                await ctx.message.author.send(embed=embed)
                confMsg = await ctx.send("Please check your DMs.")
            else:
                confMsg = await ctx.send("Sorry {}, you have no highlighted words "
                                         "currently".format(userName))
        await self._sleepThenDelete(confMsg, 5)

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
                confMsg = await ctx.send("{} added to the blacklist, "
                                         "{}".format(user.name, userName))
            else:
                confMsg = await ctx.send("This user is already on the blacklist!")
        await ctx.message.delete()
        await self._sleepThenDelete(confMsg, 5)

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
                confMsg = await ctx.send("{} removed from blacklist, "
                                         "{}".format(user.name, userName))
            else:
                confMsg = await ctx.send("This user is not on the blacklist!")
        await ctx.message.delete()
        await self._sleepThenDelete(confMsg, 5)

    @userBlacklist.command(name="clear", aliases=["cls"])
    @commands.guild_only()
    async def userBlClear(self, ctx: Context):
        """Clear your user blacklist.  Will ask for confirmation."""
        await ctx.send("Are you sure you want to clear your blacklist?  Type "
                       "`yes` to continue, otherwise type something else.")

        def check(msg):
            return (msg.author == ctx.message.author and
                    msg.channel == ctx.message.channel)

        response = await self.bot.wait_for("message", timeout=10, check=check)

        if response.content.lower() == "yes":
            async with self.config.member(ctx.author).blacklist() as userBl:
                userBl.clear()
            await ctx.send("Your highlight blacklist was cleared.")
        else:
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

                embed = discord.Embed(description=msg,
                                      colour=discord.Colour.red())
                embed.title = "Blacklisted users on {}".format(ctx.message.guild.name)
                embed.set_author(name=userName,
                                 icon_url=ctx.message.author.avatar_url)
                await ctx.message.author.send(embed=embed)
                confMsg = await ctx.send("Please check your DMs.")
            else:
                confMsg = await ctx.send("Sorry {}, you have no backlisted users "
                                         "currently".format(userName))
            await self._sleepThenDelete(confMsg, 5)

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
            await ctx.send("Please specifiy a timeout between 0 and 3600 seconds!")
            return

        guildId = ctx.message.guild.id
        userId = ctx.message.author.id

        await self.config.member(ctx.author).timeout.set(seconds)

        confMsg = await ctx.send("Timeout set to {} seconds.".format(seconds))
        await ctx.message.delete()
        await self._sleepThenDelete(confMsg, 5)


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
        self.logger.debug("Timeout %s, last triggered %s, message timestamp %s",
                     timeoutVal, lastTrig, msg.created_at)
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

        guildId = msg.guild.id
        userId = msg.author.id
        user = msg.author
        channelBlId = await self.config.guild(msg.channel.guild).ignoreChannelID()

        # Prevents messages in a blacklisted channel from triggering highlight word
        if channelBlId and msg.channel.id == channelBlId:
            return

        # Prevent bots from triggering your highlight word.
        if user.bot:
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
        except aiohttp.ClientResponseError as error:
            self.logger.error("Client response error within discord.py!", exc_info=True)
            self.logger.error(error)
        except aiohttp.ServerDisconnectedError:
            self.logger.error("Server disconnect error within discord.py!", exc_info=True)
            self.logger.error(error)

        # Iterate through every user's words on the guild, and notify all highlights
        guildData = await self.config.all_members(msg.guild)
        for currentUserId, data in guildData.items():
            # Handle case where message author has been blacklisted by the user.
            if KEY_BLACKLIST in data.keys() and msg.author.id in data[KEY_BLACKLIST]:
                continue

            for word in data[KEY_WORDS]:
                active = _isActive(currentUserId, msg, activeMessages)
                match = _isWordMatch(word, msg.content)
                timeout = data[KEY_TIMEOUT] if KEY_TIMEOUT in data.keys() else DEFAULT_TIMEOUT
                triggeredRecently = self._triggeredRecently(msg, currentUserId, timeout)
                if match and not active and not triggeredRecently \
                        and userId != currentUserId:
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

        await asyncio.gather(*tasks) # pylint: disable=no-member

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
        notifyMsg = ("In #{1.channel.name}, you were mentioned with highlight word "
                     "**{0}**:".format(word, message))
        embedMsg = ""
        msgStillThere = False
        for msg in msgContext:
            time = msg.created_at
            time = time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%H:%M:%S %Z')
            escapedMsg = chat_formatting.escape(msg.content, formatting=True)
            embedMsg += ("[{0}] {1.author.name}#{1.author.discriminator}: {2}"
                         "\n".format(time, msg, escapedMsg))
            if _isWordMatch(word, msg.content):
                msgStillThere = True
        if not msgStillThere:
            return
        embed = discord.Embed(title=user.name, description=embedMsg,
                              colour=discord.Colour.red())
        embed.add_field(name="Context", value="[Click to Jump]({})".format(msgUrl))
        time = message.created_at.replace(tzinfo=timezone.utc).astimezone(tz=None)
        footer = "Triggered at | {}".format(time.strftime('%a, %d %b %Y %I:%M%p %Z'))
        embed.set_footer(text=footer)
        try:
            await user.send(content=notifyMsg, embed=embed)
            self.logger.info("%s#%s (%s) was successfully triggered.",
                        user.name, user.discriminator, user.id)
        except discord.errors.Forbidden as error:
            self.logger.error("Could not notify %s#%s (%s)!  They probably has DMs disabled!",
                         user.name, user.discriminator, user.id)

    # Event listeners
    @commands.Cog.listener()
    async def on_message(self, msg):
        await self.checkHighlights(msg)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Background listener to check if dark-hour has been created"""
        self.logger.info("New Channel creation has been detected. Name: %s, ID: %s",
                         channel.name, channel.id)
        if channel.name == "dark-hour":
            await self.config.guild(channel.guild).ignoreChannelID.set(channel.id)
            self.logger.info("Dark hour has been detected and channel id %s "
                             "will be blacklisted from highlights.", channel.id)
        else:
            self.logger.info("New channel is not called dark hour and will not be "
                             "blacklisted")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Background listener to check if dark-hour has been deleted"""
        channelBlId = await self.config.guild(channel.guild).ignoreChannelID()
        if channelBlId and channel.id == channelBlId:
            await self.config.guild(channel.guild).ignoreChannelID.set(None)
            self.logger.info("Dark hour deletion has been detected and channelBlId has "
                             "been reset")
        else:
            self.logger.info("Deleted channel is not dark hour so dark hour ID remains "
                             "unchanged")

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

def _isWordMatch(word, string):
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
        regex = r'\b{}\b'.format(re.escape(word.lower()))
        return bool(re.search(regex, string.lower()))
    except Exception as error: # pylint: disable=broad-except
        self.logger.error("Regex error: %s", word)
        self.logger.error(error)
        return False
