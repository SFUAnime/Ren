"""Highlights cog: DM a user certain "highlight" words that they specify.

Credit: This idea was first implemented by Danny (https://github.com/Rapptz/) but at
the time, that bot was closed source.
"""
from copy import deepcopy
from datetime import timedelta, timezone
import itertools
import os
import re
from threading import Lock
import asyncio
from aiohttp import errors as aiohttpErrors
import discord
from discord.ext import commands
from cogs.utils import config
from cogs.utils.dataIO import dataIO

MAX_WORDS = 5
KEY_GUILDS = "guilds"
KEY_WORDS = "words"

def checkFilesystem():
    """Check if the folders/files are created."""
    folders = ["data/highlight"]
    for folder in folders:
        if not os.path.exists(folder):
            print("Highlight: Creating folder: {} ...".format(folder))
            os.makedirs(folder)

    files = ["data/highlight/words.json"]
    for theFile in files:
        if not os.path.exists(theFile):
            if "words" in theFile:
                #build a default words.json
                myDict = {}
                myDict['guilds'] = []
                dataIO.save_json("data/highlight/words.json", myDict)

            print("Highlight: Creating file: {} ...".format(theFile))

class Highlight(object):
    def __init__(self, bot):
        self.bot = bot
        self.lock = Lock()
        self.settings = config.Config("settings.json",
                                      cogname="lui-cogs/highlight")
        self.highlights = self.settings.get(KEY_GUILDS) if not None else {}
        # previously: dataIO.load_json("data/highlight/words.json")
        self.wordFilter = None

    def _update_highlights(self, new_obj):
        self.lock.acquire()
        try:
            dataIO.save_json("data/highlight/words.json", new_obj)
            self.highlights = dataIO.load_json("data/highlight/words.json")
        finally:
            self.lock.release()

    async def _sleep_then_delete(self, msg, time):
        await asyncio.sleep(time)
        await self.bot.delete_message(msg)

    def _get_guild_ids(self):
        guilds = [list(x) for x in self.highlights['guilds']]
        return list(itertools.chain.from_iterable(guilds)) # flatten list

    def _check_guilds(self, guild_id):
        """returns guild pos in list"""
        guilds_ids = self._get_guild_ids()

        if guild_id not in guilds_ids:
            new_guild = {}
            users = {}
            users['users'] = []
            new_guild[guild_id] = users
            self.highlights['guilds'].append(new_guild)
            self._update_highlights(self.highlights)

        return next(x for (x, d) in enumerate(self.highlights['guilds']) if guild_id in d)

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
            self.highlights[guildId][userId] = {KEY_WORDS: []}

    @commands.group(name="highlight", pass_context=True, no_pm=True)
    async def highlight(self, ctx):
        """Slack-like feature to be notified based on specific words outside of at-mentions"""
        if not ctx.invoked_subcommand:
            await self.bot.send_cmd_help(ctx)

    @highlight.command(name="add", pass_context=True, no_pm=True)
    async def addHighlight(self, ctx, word: str):
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
        await self._sleep_then_delete(confMsg, 5)

    @highlight.command(name="del", pass_context=True, no_pm=True,
                       aliases=["delete", "remove", "rm"])
    async def removeHighlight(self, ctx, word: str):
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
        await self._sleep_then_delete(confMsg, 5)

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
        await self._sleep_then_delete(confMsg, 5)

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
            prevServerWords = self.highlights[guildId][userId][KEY_WORDS]

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
        await self._sleep_then_delete(confMsg, 5)

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
        # Iterate through every user's words on the server, and notify all highlights
        for currentUserId, data in self.highlights[guildId].items():
            for word in data[KEY_WORDS]:
                active = await self._isActive(currentUserId, msg)
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

        await asyncio.gather(*tasks)

    async def _notifyUser(self, user, message, word):
        """Notify the user of the triggered highlight word."""
        msgs = []
        try:
            async for msg in self.bot.logs_from(message.channel, limit=6, around=message):
                msgs.append(msg)
        except aiohttpErrors.ClientResponseError:
            # TODO: Add logger.
            pass
        except aiohttpErrors.ServerDisconnectedError:
            # TODO: Add logger.
            pass
        msgContext = sorted(msgs, key=lambda r: r.timestamp)
        msgUrl = "https://discordapp.com/channels/{}/{}/{}".format(message.server.id,
                                                                   message.channel.id,
                                                                   message.id)
        notifyMsg = ("In {1.channel.mention}, you were mentioned with highlight word **{0}**:\n"
                     "Jump: {2}".format(word, message, msgUrl))
        embedMsg = ""
        msgStillThere = False
        for msg in msgContext:
            time = msg.timestamp
            time = time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%H:%M:%S %Z')
            embedMsg += ("[{0}] {1.author.name}#{1.author.discriminator}: {1.content}"
                         "\n".format(time, msg))
            if _isWordMatch(word, msg.content):
                msgStillThere = True
        if not msgStillThere:
            return
        embed = discord.Embed(title=user.name, description=embedMsg,
                              colour=discord.Colour.red())
        time = message.timestamp.replace(tzinfo=timezone.utc).astimezone(tz=None)
        footer = "Triggered at | {}".format(time.strftime('%a, %d %b %Y %I:%M%p %Z'))
        embed.set_footer(text=footer)
        await self.bot.send_message(user, content=notifyMsg, embed=embed)

    async def _isActive(self, userId, message):
        """Checks to see if the user has been active on a channel,
        given a message from a channel.

        Parameters:
        -----------
        userId: int
            The user ID we wish to check.
        message: discord.Message
            The discord message object that we wish to check the user against.
        """
        isActive = False
        try:
            async for msg in self.bot.logs_from(message.channel, limit=50, before=message):
                deltaSinceMsg = message.timestamp - msg.timestamp
                if msg.author.id == userId and deltaSinceMsg <= timedelta(seconds=20):
                    isActive = True
                    break
        except aiohttpErrors.ClientResponseError:
            # TODO: Add logger.
            isActive = False
        except aiohttpErrors.ServerDisconnectedError:
            # TODO: Add logger.
            isActive = False
        return isActive

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
        print("Highlight error: Using the word \"{}\"".format(word))
        print(error)
        return False

def setup(bot):
    """Add the cog to the bot."""
    checkFilesystem()
    hilite = Highlight(bot)
    bot.add_listener(hilite.checkHighlights, 'on_message')
    bot.add_cog(hilite)
