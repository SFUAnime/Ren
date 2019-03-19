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
from aiohttp import errors as aiohttpErrors
import discord
from discord.ext import commands
from cogs.utils import config, chat_formatting
from cogs.utils.dataIO import dataIO

ACTIVE_TIME = 20
LOGGER = None
MAX_WORDS = 5
KEY_GUILDS = "guilds"
KEY_BLACKLIST = "blacklist"
KEY_WORDS = "words"
SAVE_FOLDER = "data/lui-cogs/highlight/"
SAVE_FILE = "settings.json"

def checkFilesystem():
    """Check if the folders/files are created."""
    if not os.path.exists(SAVE_FOLDER):
        print("Highlight: Creating folder: {} ...".format(SAVE_FOLDER))
        os.makedirs(SAVE_FOLDER)

    theFile = SAVE_FOLDER + SAVE_FILE
    if not dataIO.is_valid_json(theFile):
        print("Creating default highlight settings.json...")
        dataIO.save_json(theFile, {})

class Highlight:
    """Slack-like feature to be notified based on specific words."""
    def __init__(self, bot):
        self.bot = bot
        self.lock = Lock()
        self.settings = config.Config("settings.json",
                                      cogname="lui-cogs/highlight")
        self.highlights = self.settings.get(KEY_GUILDS)
        self.highlights = {} if not self.highlights else self.highlights
        # previously: dataIO.load_json("data/highlight/words.json")
        self.wordFilter = None

    async def _sleepThenDelete(self, msg, time):
        await asyncio.sleep(time) # pylint: disable=no-member
        await self.bot.delete_message(msg)

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
            self.highlights[guildId][userId] = {KEY_WORDS: [], KEY_BLACKLIST: []}
            return

        if KEY_BLACKLIST not in self.highlights[guildId][userId].keys():
            self.highlights[guildId][userId][KEY_BLACKLIST] = []

    @commands.group(name="highlight", pass_context=True, no_pm=True,
                    aliases=["hl"])
    async def highlight(self, ctx):
        """Slack-like feature to be notified based on specific words outside of at-mentions"""
        if not ctx.invoked_subcommand:
            await self.bot.send_cmd_help(ctx)

    @highlight.command(name="add", pass_context=True, no_pm=True)
    async def addHighlight(self, ctx, *, word: str):
        """Add a word to be highlighted in the current guild"""
        with self.lock:
            guildId = ctx.message.server.id
            userId = ctx.message.author.id
            userName = ctx.message.author.name

            self._registerUser(guildId, userId)
            userWords = self.highlights[guildId][userId][KEY_WORDS]

            if len(userWords) <= MAX_WORDS and word not in userWords:
                # user can only have MAX_WORDS words
                userWords.append(word)
                confMsg = await self.bot.say("Highlight word added, {}".format(userName))
            else:
                confMsg = await self.bot.say("Sorry {}, you already have {} words "
                                             "highlighted, or you are trying to add "
                                             "a duplicate word".format(userName,
                                                                       MAX_WORDS))
            await self.bot.delete_message(ctx.message)
            await self.settings.put(KEY_GUILDS, self.highlights)
        await self._sleepThenDelete(confMsg, 5)

    @highlight.command(name="del", pass_context=True, no_pm=True,
                       aliases=["delete", "remove", "rm"])
    async def removeHighlight(self, ctx, *, word: str):
        """Remove a highlighted word in the current guild"""
        with self.lock:
            guildId = ctx.message.server.id
            userId = ctx.message.author.id
            userName = ctx.message.author.name

            self._registerUser(guildId, userId)
            userWords = self.highlights[guildId][userId][KEY_WORDS]

            if word in userWords:
                userWords.remove(word)
                confMsg = await self.bot.say("Highlight word removed, {}".format(userName))
            else:
                confMsg = await self.bot.say("Sorry {}, you don't have this word "
                                             "highlighted".format(userName))
            await self.bot.delete_message(ctx.message)
            await self.settings.put(KEY_GUILDS, self.highlights)
        await self._sleepThenDelete(confMsg, 5)

    @highlight.command(name="list", pass_context=True, no_pm=True, aliases=["ls"])
    async def listHighlight(self, ctx):
        """List your highighted words for the current guild"""
        guildId = ctx.message.server.id
        userId = ctx.message.author.id
        userName = ctx.message.author.name

        self._registerUser(guildId, userId)
        userWords = self.highlights[guildId][userId][KEY_WORDS]

        if userWords:
            msg = ""
            for word in userWords:
                msg += "{}\n".format(word)

            embed = discord.Embed(description=msg,
                                  colour=discord.Colour.red())
            embed.set_author(name=ctx.message.author.name,
                             icon_url=ctx.message.author.avatar_url)
            confMsg = await self.bot.say(embed=embed)
        else:
            confMsg = await self.bot.say("Sorry {}, you have no highlighted words "
                                         "currently".format(userName))
        await self._sleepThenDelete(confMsg, 5)

    @highlight.group(name="blacklist", pass_context=True, no_pm=True,
                     aliases=["bl"])
    async def userBlacklist(self, ctx):
        """Blacklist certain users from triggering your words."""
        if str(ctx.invoked_subcommand).lower() == "highlight blacklist":
            await self.bot.send_cmd_help(ctx)

    @userBlacklist.command(name="add", pass_context=True, no_pm=True)
    async def userBlAdd(self, ctx, user: discord.Member):
        """Add a user to your blacklist.

        Parameters:
        -----------
        user: discord.Member
            The user you wish to block from triggering your highlight words.
        """
        with self.lock:
            guildId = ctx.message.server.id
            userId = ctx.message.author.id
            userName = ctx.message.author.name

            self._registerUser(guildId, userId)
            userBl = self.highlights[guildId][userId][KEY_BLACKLIST]

            if user.id not in userBl:
                userBl.append(user.id)
                confMsg = await self.bot.say("{} added to the blacklist, "
                                             "{}".format(user.name, userName))
            else:
                confMsg = await self.bot.say("This user is already on the blacklist!")
            await self.bot.delete_message(ctx.message)
            await self.settings.put(KEY_GUILDS, self.highlights)
        await self._sleepThenDelete(confMsg, 5)

    @userBlacklist.command(name="del", pass_context=True, no_pm=True,
                           aliases=["delete", "remove", "rm"])
    async def userBlRemove(self, ctx, user: discord.Member):
        """Remove a user from your blacklist.

        Parameters:
        -----------
        user: discord.Member
            The user you wish to remove from your blacklist.
        """
        with self.lock:
            guildId = ctx.message.server.id
            userId = ctx.message.author.id
            userName = ctx.message.author.name

            self._registerUser(guildId, userId)
            userBl = self.highlights[guildId][userId][KEY_BLACKLIST]

            if user.id in userBl:
                userBl.remove(user.id)
                confMsg = await self.bot.say("{} removed from blacklist, "
                                             "{}".format(user.name, userName))
            else:
                confMsg = await self.bot.say("This user is not on the blacklist!")
            await self.bot.delete_message(ctx.message)
            await self.settings.put(KEY_GUILDS, self.highlights)
        await self._sleepThenDelete(confMsg, 5)

    @userBlacklist.command(name="clear", pass_context=True, no_pm=True,
                           aliases=["cls"])
    async def userBlClear(self, ctx):
        """Clear your user blacklist.  Will ask for confirmation."""
        await self.bot.say("Are you sure you want to clear your blacklist?  Type "
                           "`yes` to continue, otherwise type something else.")
        response = await self.bot.wait_for_message(timeout=10, author=ctx.message.author,
                                                   channel=ctx.message.channel)

        if response.content.lower() == "yes":
            with self.lock:
                guildId = ctx.message.server.id
                userId = ctx.message.author.id

                self._registerUser(guildId, userId)
                self.highlights[guildId][userId][KEY_BLACKLIST].clear()
                await self.settings.put(KEY_GUILDS, self.highlights)
                await self.bot.say("Your highlight blacklist was cleared.")
        else:
            await self.bot.say("Not clearing your blacklist.")

    @userBlacklist.command(name="list", pass_context=True, no_pm=True,
                           aliases=["ls"])
    async def userBlList(self, ctx):
        """List the users on your blacklist."""
        guildId = ctx.message.server.id
        userId = ctx.message.author.id
        userName = ctx.message.author.name

        self._registerUser(guildId, userId)
        userBl = self.highlights[guildId][userId][KEY_BLACKLIST]

        if userBl:
            msg = ""
            for userId in userBl:
                userObj = discord.utils.get(ctx.message.server.members, id=userId)
                if not userObj:
                    continue
                msg += "{}\n".format(userObj.name)
            if msg == "":
                msg = "You have blacklisted users that are no longer in the guild."

            embed = discord.Embed(description=msg,
                                  colour=discord.Colour.red())
            embed.title = "Blacklisted users on {}".format(ctx.message.server.name)
            embed.set_author(name=ctx.message.author.name,
                             icon_url=ctx.message.author.avatar_url)
            await self.bot.send_message(ctx.message.author, embed=embed)
            confMsg = await self.bot.say("Please check your DMs.")
        else:
            confMsg = await self.bot.say("Sorry {}, you have no backlisted users "
                                         "currently".format(userName))
        await self._sleepThenDelete(confMsg, 5)

    @highlight.command(name="import", pass_context=True, no_pm=False)
    async def importHighlight(self, ctx, fromServer: str):
        """Transfer highlights from a different guild to the current guild.
        This OVERWRITES any words in the current guild.

        Parameters:
        -----------
        fromServer: str
            The name of the server you wish to import from.
        """
        with self.lock:
            guildId = ctx.message.server.id
            userId = ctx.message.author.id
            userName = ctx.message.author.name

            self._registerUser(guildId, userId)

            importGuild = discord.utils.get(self.bot.servers, name=fromServer)

            if not importGuild:
                await self.bot.say("The server you wanted to import from is not "
                                   "in the list of servers I'm in.")
                return

            self._registerUser(importGuild.id, userId)

            if not self.highlights[importGuild.id][userId][KEY_WORDS]:
                await self.bot.say("You don't have any words from the server you "
                                   "wish to import from!")
                return
            importWords = self.highlights[importGuild.id][userId][KEY_WORDS]
            self.highlights[guildId][userId][KEY_WORDS] = deepcopy(importWords)
            confMsg = await self.bot.say("Highlight words imported from {} for "
                                         "{}".format(fromServer,
                                                     userName))
            await self.settings.put(KEY_GUILDS, self.highlights)
        await self._sleepThenDelete(confMsg, 5)

    async def checkHighlights(self, msg):
        """Background listener to check if a highlight has been triggered."""
        if isinstance(msg.channel, discord.PrivateChannel):
            return

        guildId = msg.server.id
        userId = msg.author.id
        user = msg.author

        # Prevent bots from triggering your highlight word.
        if user.bot:
            return

        # Don't send notification for filtered messages
        if not self.wordFilter:
            self.wordFilter = self.bot.get_cog("WordFilter")
        elif self.wordFilter.containsFilterableWords(msg):
            return

        tasks = []

        if guildId not in self.highlights.keys():
            # Skip if the guild is not initialized.
            return
        activeMessages = []
        try:
            async for message in self.bot.logs_from(msg.channel, limit=50, before=msg):
                activeMessages.append(message)
        except aiohttpErrors.ClientResponseError as error:
            LOGGER.error("Client response error within discord.py!")
            LOGGER.error(error)
        except aiohttpErrors.ServerDisconnectedError:
            LOGGER.error("Server disconnect error within discord.py!")
            LOGGER.error(error)

        # Iterate through every user's words on the server, and notify all highlights
        for currentUserId, data in self.highlights[guildId].items():
            # Handle case where message author has been blacklisted by the user.
            if KEY_BLACKLIST in data.keys() and msg.author.id in data[KEY_BLACKLIST]:
                continue

            for word in data[KEY_WORDS]:
                active = _isActive(currentUserId, msg, activeMessages)
                match = _isWordMatch(word, msg.content)
                if match and not active and userId != currentUserId:
                    hiliteUser = msg.server.get_member(currentUserId)
                    if not hiliteUser:
                        # Handle case where user is no longer in the server of interest.
                        continue
                    perms = msg.channel.permissions_for(hiliteUser)
                    if not perms.read_messages:
                        # Handle case where user cannot see the channel.
                        break
                    tasks.append(self._notifyUser(hiliteUser, msg, word))

        await asyncio.gather(*tasks) # pylint: disable=no-member

    async def _notifyUser(self, user, message, word):
        """Notify the user of the triggered highlight word."""
        msgs = []
        try:
            async for msg in self.bot.logs_from(message.channel, limit=6, around=message):
                msgs.append(msg)
        except aiohttpErrors.ClientResponseError as error:
            LOGGER.error("Client response error within discord.py!")
            LOGGER.error(error)
        except aiohttpErrors.ServerDisconnectedError as error:
            LOGGER.error("Server disconnect error within discord.py!")
            LOGGER.error(error)
        msgContext = sorted(msgs, key=lambda r: r.timestamp)
        msgUrl = "https://discordapp.com/channels/{}/{}/{}".format(message.server.id,
                                                                   message.channel.id,
                                                                   message.id)
        notifyMsg = ("In {1.channel.mention}, you were mentioned with highlight word "
                     "**{0}**:".format(word, message))
        embedMsg = ""
        msgStillThere = False
        for msg in msgContext:
            time = msg.timestamp
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
        time = message.timestamp.replace(tzinfo=timezone.utc).astimezone(tz=None)
        footer = "Triggered at | {}".format(time.strftime('%a, %d %b %Y %I:%M%p %Z'))
        embed.set_footer(text=footer)
        try:
            await self.bot.send_message(user, content=notifyMsg, embed=embed)
            LOGGER.info("%s#%s (%s) was successfully triggered.",
                        user.name, user.discriminator, user.id)
        except discord.errors.Forbidden as error:
            LOGGER.error("Could not notify %s#%s (%s)!  They probably has DMs disabled!",
                         user.name, user.discriminator, user.id)

def _isActive(userId, originalMessage, messages):
    """Checks to see if the user has been active on a channel,
    given a message from a channel.

    Parameters:
    -----------
    userId: int
        The user ID we wish to check.
    originalMessage: discord.Message
        The original message whose base timestamp we wish to check against.
    messages: [ discord.Message ]
        A list of discord message objects that we wish to check the user against.

    Returns:
    --------
    bool
        True, if the user has spoken ACTIVE_TIME seconds before originalMessage.
        False, otherwise.
    """
    for msg in messages:
        deltaSinceMsg = originalMessage.timestamp - msg.timestamp
        if msg.author.id == userId and deltaSinceMsg <= timedelta(seconds=ACTIVE_TIME):
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
        LOGGER.error("Regex error: %s", word)
        LOGGER.error(error)
        return False

def setup(bot):
    """Add the cog to the bot."""
    checkFilesystem()
    hilite = Highlight(bot)
    global LOGGER # pylint: disable=global-statement
    LOGGER = logging.getLogger("red.Highlight")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/lui-cogs/highlight/info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    bot.add_listener(hilite.checkHighlights, 'on_message')
    bot.add_cog(hilite)
