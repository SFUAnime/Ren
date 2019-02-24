"""Highlights cog: DM a user certain "highlight" words that they specify.

Credit: This idea was first implemented by Danny (https://github.com/Rapptz/) but at
the time, that bot was closed source.
"""
from datetime import timedelta, timezone
import itertools
import os
import re
from threading import Lock
import asyncio
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
            await self.settings.put(KEY_GUILD, self.highlights)
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
            await self.settings.put(KEY_GUILD, self.highlights)
        await self._sleep_then_delete(confMsg, 5)

    @highlight.command(name="list", pass_context=True, no_pm=True, aliases=["ls"])
    async def list_highlight(self, ctx):
        """List your highighted words for the current guild"""
        guild_id = ctx.message.server.id
        user_id = ctx.message.author.id
        user_name = ctx.message.author.name

        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)

        if user is not None:
            user_list = user[1]
            if len(user_list['words']) > 0:
                msg = ""
                for word in user_list['words']:
                    msg += word
                    msg += "\n"

                embed = discord.Embed(description=msg,colour=discord.Colour.red())
                embed.set_author(name=ctx.message.author.name,icon_url=ctx.message.author.avatar_url)
                t_msg = await self.bot.say(embed=embed)
                await self._sleep_then_delete(t_msg,5)
            else:
                t_msg = await self.bot.say("Sorry {}, you have no highlighted words currently".format(user_name))
                await self._sleep_then_delete(t_msg,5)
        else:
            msg = "Sorry {}, you aren't currently registered for highlights."
            msg += " Add a word to become registered"
            t_msg = await self.bot.say(msg.format(user_name))
            await self._sleep_then_delete(t_msg,5)

    @highlight.command(name="import", pass_context=True, no_pm=False)
    async def import_highlight(self, ctx, from_server: str):
        """Transfer highlights from a different guild to the current guild, OVERWRITING any words in the current guild"""
        guild_id = ctx.message.server.id
        user_id = ctx.message.author.id
        user_name = ctx.message.author.name

        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)

        guild = discord.utils.get(self.bot.servers, name=from_server)

        # This is kind of ugly, dont really like it but kind of has to be done like this based on how i have
        # the highlight data structured, will definitely be revisting this
        if guild is not None and user is not None:
            user_idx = user[0]
            if guild.id in self._get_guild_ids():
                impt_guild_idx = self._check_guilds(guild.id)
                impt_user = self._is_registered(impt_guild_idx,guild.id,user_id)

                if impt_user is not None:
                    impt_user_idx = impt_user[0]
                    impt = self.highlights['guilds'][impt_guild_idx][guild.id]['users'][impt_user_idx]
                    self.highlights['guilds'][guild_idx][guild_id]['users'][user_idx] = impt
                    self._update_highlights(self.highlights)
                    t_msg = await self.bot.say("Highlight words imported from {0} for {1}".format(from_server,user_name))
                    await self._sleep_then_delete(t_msg,3)
            else:
                msg = "Sorry {}, the guild you want to import from"
                msg += " is not registered for highlights, or you are not registered in that guild"
                t_msg = await self.bot.say(msg.format(user_name))
                await self._sleep_then_delete(t_msg,5)
        else:
            msg = "Sorry {}, this bot is not in the guild you want to import from,"
            msg += " or you are not registered in this guild"
            t_msg = await self.bot.say(msg.format(user_name))
            await self._sleep_then_delete(t_msg,5)

    async def check_highlights(self, msg):
        if isinstance(msg.channel,discord.PrivateChannel):
            return

        guild_id = msg.server.id
        user_id = msg.author.id
        user_obj = msg.author

        guild_idx = self._check_guilds(guild_id)

        # Prevent bots from triggering your highlight word.
        if user_obj.bot:
            return

        # Don't send notification for filtered messages  
        if not self.wordFilter:
            self.wordFilter = self.bot.get_cog("WordFilter")
        elif self.wordFilter.containsFilterableWords(msg):
            return

        tasks = []
        # iterate through every users words on the server, and notify all highlights
        for user in self.highlights['guilds'][guild_idx][guild_id]['users']:
            for word in user['words']:
                active = await self._is_active(user['id'],msg.channel,msg)
                match = self._is_word_match(word,msg.content)
                if match and not active and user_id != user['id']:
                    hilite_user = msg.server.get_member(user['id'])
                    if hilite_user is None:
                        # Handle case where user is no longer in the server of interest.
                        continue
                    perms = msg.channel.permissions_for(hilite_user)
                    if not perms.read_messages:
                        break
                    tasks.append(self._notify_user(hilite_user,msg,word))

        await asyncio.gather(*tasks)

    async def _notify_user(self, user, message, word):
        msgs = []
        async for msg in self.bot.logs_from(message.channel,limit=6,around=message):
            msgs.append(msg)
        msg_ctx = sorted(msgs, key=lambda r: r.timestamp)
        msgUrl = "https://discordapp.com/channels/{}/{}/{}".format(message.server.id,
                                                                   message.channel.id,
                                                                   message.id)
        notify_msg = ("In {1.channel.mention}, you were mentioned with highlight word **{0}**:\n"
                      "Jump: {2}".format(word, message, msgUrl))
        embed_msg = ""
        msg_still_there = False
        for msg in msg_ctx:
            time = msg.timestamp
            time = time.replace(tzinfo=timezone.utc).astimezone(tz=None).strftime('%H:%M:%S %Z')
            embed_msg += "[{0}] {1.author.name}#{1.author.discriminator}: {1.content}\n".format(time,msg)
            if self._is_word_match(word, msg.content):
                msg_still_there = True
        if not msg_still_there:
            return
        embed = discord.Embed(title=user.name,description=embed_msg,colour=discord.Colour.red())
        time = message.timestamp.replace(tzinfo=timezone.utc).astimezone(tz=None)
        footer = "Triggered at | {}".format(time.strftime('%a, %d %b %Y %I:%M%p %Z'))
        embed.set_footer(text=footer)
        await self.bot.send_message(user,content=notify_msg,embed=embed)

    def _is_word_match(self, word, string):
        try:
            regex = r'\b{}\b'.format(re.escape(word.lower()))
            return bool(re.search(regex,string.lower()))
        except Exception as e:
            print("Highlight error: Using the word \"{}\"".format(word))
            print(e)

    async def _is_active(self, user_id, channel, message):
        is_active = False

        async for msg in self.bot.logs_from(channel,limit=50,before=message):
            delta_since_msg = message.timestamp - msg.timestamp
            if msg.author.id == user_id and delta_since_msg <= timedelta(seconds=20):
                is_active = True
                break
        return is_active

def setup(bot):
    checkFilesystem()
    hilite = Highlight(bot)
    bot.add_listener(hilite.check_highlights, 'on_message')
    bot.add_cog(hilite)
