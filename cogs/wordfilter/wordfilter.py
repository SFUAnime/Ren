"""Word Filter cog.
To filter words in a more smart/useful wya than simply detecting and
deleting a message.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""
import re
from threading import Lock
import logging
import asyncio
import random
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.utils import paginator
from redbot.core.bot import Red

COLOUR = discord.Colour
COLOURS = [COLOUR.purple(), COLOUR.red(), COLOUR.blue(), COLOUR.orange(), COLOUR.green()]
PATTERN_CHANNEL_ID = r"<#(\d+)>"
BASE = {"channelAllowed": [], "filters": [], "commandDenied": [], "toggleMod": False}


class WordFilter(commands.Cog):  # pylint: disable=too-many-instance-attributes
    """Word Filter cog, for all your word filtering needs."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE)  # Register default (empty) settings.

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.WordFilter")
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

        # self.commandBlacklist = dataIO.load_json(PATH_BLACKLIST)
        # self.filters = dataIO.load_json(PATH_FILTER)
        # self.whitelist = dataIO.load_json(PATH_WHITELIST)
        # self.settings = dataIO.load_json(PATH_SETTINGS)

    @commands.group(name="wordfilter", aliases=["wf"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def wordFilter(self, ctx):
        """Smart word filtering"""

    @wordFilter.group(name="regex", aliases=["re"])
    async def regex(self, ctx):
        """Regular expression (regex) settings.

        These commands allow you to manipulate the regex used to filter
        out messages.
        """

    @regex.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def addFilter(self, ctx, word: str):
        """Add a regex to the filter.

        Parameters:
        -----------
        word: str
            The regex string you would like to add to the filter.
        """
        user = ctx.message.author
        guildName = ctx.message.guild.name
        filters = await self.config.guild(ctx.guild).filters()

        if word not in filters:
            filters.append(word)
            await self.config.guild(ctx.guild).filters.set(filters)
            await user.send(
                "`Word Filter:` `{0}` was added to the filter in the "
                "guild **{1}**".format(word, guildName)
            )
        else:
            await user.send(
                "`Word Filter:` The word `{0}` is already in the filter "
                "for guild **{1}**".format(word, guildName)
            )

    @regex.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def removeFilter(self, ctx, word: str):
        """Remove a regex from the filter.

        Parameters:
        -----------
        word: str
            The regex string you would like to remove from the filter.
        """
        user = ctx.message.author
        guildName = ctx.message.guild.name
        filters = await self.config.guild(ctx.guild).filters()

        if not filters or word not in filters:
            await user.send(
                "`Word Filter:` The word `{0}` is not in the filter for "
                "guild **{1}**".format(word, guildName)
            )
        else:
            filters.remove(word)
            await self.config.guild(ctx.guild).filters.set(filters)
            await user.send(
                "`Word Filter:` `{0}` removed from the filter in the "
                "guild **{1}**".format(word, guildName)
            )

    @regex.command(name="list", aliases=["ls"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def listFilter(self, ctx):
        """List the regex used to filter messages in raw format.
        NOTE: do this in a channel outside of the viewing public
        """
        guildName = ctx.message.guild.name
        user = ctx.message.author
        filters = await self.config.guild(ctx.guild).filters()

        if filters:
            display = []
            for regex in filters:
                display.append("`{}`".format(regex))

            page = paginator.Pages(ctx=ctx, entries=display, show_entry_count=True)
            page.embed.title = "Filtered words for: **{}**".format(guildName)
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await user.send("Sorry you have no filtered words in **{}**".format(guildName))

    @wordFilter.command(name="togglemod")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def toggleMod(self, ctx):
        """Toggle global override of filters for server admins/mods."""
        toggleMod = await self.config.guild(ctx.guild).toggleMod()

        if toggleMod:
            toggleMod = False
            await ctx.send(
                ":negative_squared_cross_mark: Word Filter: Moderators "
                "(and higher) **will be** filtered."
            )
        else:
            toggleMod = True
            await ctx.send(
                ":white_check_mark: Word Filter: Moderators (and higher "
                "**will not be** filtered."
            )
        await self.config.guild(ctx.guild).toggleMod.set(toggleMod)

    #########################################
    # COMMANDS - COMMAND BLACKLIST SETTINGS #
    #########################################
    @wordFilter.group(name="command", aliases=["cmd"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _command(self, ctx):
        """Command denylist settings.

        Settings for controlling filtering on commands.
        """

    @_command.command(name="add")
    @commands.guild_only()
    async def _commandAdd(self, ctx, cmd: str):
        """Add a command (without prefix) to the denylist.
        If the invoked command contains any filtered words, the entire message
        is filtered and the contents of the message will be sent back to the
        user via DM.
        """
        cmdDenied = await self.config.guild(ctx.guild).commandDenied()

        if cmd not in cmdDenied:
            cmdDenied.append(cmd)
            await self.config.guild(ctx.guild).commandDenied.set(cmdDenied)
            await ctx.send(
                f":white_check_mark: Word Filter: Command `{cmd}` is now "
                "in the denylist.  It will have the entire message filtered "
                "if it contains any filterable regex, and its contents "
                "DM'd back to the user."
            )
        else:
            await ctx.send(
                ":negative_squared_cross_mark: Word Filter: Command "
                f"`{cmd}` is already in the denylist."
            )

    @_command.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    async def _commandRemove(self, ctx, cmd: str):
        """Remove a command from the denylist.

        The command that is removed from the list will be filtered as normal
        messages.  That is, if the invoked command contains any filterable regex,
        only the filtered regex will be censored and replaced (as opposed to the
        entire message being deleted).

        Parameters:
        -----------
        cmd: str
            The command to remove from the denylist.
        """
        guildName = ctx.message.guild.name

        cmdDenied = await self.config.guild(ctx.guild).commandDenied()

        if not cmdDenied or cmd not in cmdDenied:
            await ctx.send(
                ":negative_squared_cross_mark: Word Filter: Command "
                f"`{cmd}` wasn't on the denylist."
            )
        else:
            cmdDenied.remove(cmd)
            await self.config.guild(ctx.guild).commandDenied.set(cmdDenied)
            await ctx.send(
                f":white_check_mark: Word Filter: `{cmd}` removed from " "the command denylist."
            )

    @_command.command(name="list", aliases=["ls"])
    @commands.guild_only()
    async def _commandList(self, ctx):
        """List commands on the denylist.
        If the commands on this list are invoked with any filtered regex, the
        entire message is filtered and the contents of the message will be sent
        back to the user via DM.
        """
        guildName = ctx.message.guild.name

        cmdDenied = await self.config.guild(ctx.guild).commandDenied()

        if cmdDenied:
            display = []
            for cmd in cmdDenied:
                display.append("`{}`".format(cmd))

            page = paginator.Pages(ctx=ctx, entries=display, show_entry_count=True)
            page.embed.title = f"Denylist commands for: **{guildName}**"
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await ctx.send(f"Sorry, there are no commands on the denylist for **{guildName}**")

    ############################################
    # COMMANDS - CHANNEL WHITELISTING SETTINGS #
    ############################################
    @wordFilter.group(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _channel(self, ctx):
        """Channel allowlist settings.

        This controls channels that should not be subjected to the word filter.
        Note that this only matches the channel name, and not the actual channel
        itself. This means that if you rename a channel's name to one that matches
        on this list, it WILL NOT be subjected to filtering.
        """

    @_channel.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _channelAdd(self, ctx, channelName):
        """Add a channel to the allowlist.

        All messages in the channel will not be filtered.

        Parameters:
        -----------
        channelName: str
            The channel to add to the allowlist.
        """
        guildId = ctx.message.guild.id
        channelAllowed = await self.config.guild(ctx.guild).channelAllowed()

        match = re.search(PATTERN_CHANNEL_ID, channelName)
        if match:  # channel ID
            channel = discord.utils.get(ctx.message.guild.channels, id=match.group(1))
            channelName = channel.name

        if channelName not in channelAllowed:
            channelAllowed.append(channelName)
            await self.config.guild(ctx.guild).channelAllowed.set(channelAllowed)
            await ctx.send(
                ":white_check_mark: Word Filter: Channel with name "
                f"`{channelName}` will not be filtered."
            )
        else:
            await ctx.send(
                ":negative_squared_cross_mark: Word Filter: Channel "
                f"`{channelName}` is already on the allowlist."
            )

    @_channel.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _channelRemove(self, ctx, channelName):
        """Remove a channel from the allowlist.

        All messages in the removed channel will be subjected to the filter.

        Parameters:
        -----------
        channelName: str
            The channel to remove from the allowlist.
        """
        guildName = ctx.message.guild.name

        channelAllowed = await self.config.guild(ctx.guild).channelAllowed()

        match = re.search(PATTERN_CHANNEL_ID, channelName)
        if match:  # channel ID
            channel = discord.utils.get(ctx.message.guild.channels, id=match.group(1))
            channelName = channel.name

        if not channelAllowed or channelName not in channelAllowed:
            await ctx.send(
                ":negative_squared_cross_mark: Word Filter: Channel "
                f"`{channelName}` is not on the allowlist."
            )
        else:
            channelAllowed.remove(channelName)
            await self.config.guild(ctx.guild).channelAllowed.set(channelAllowed)
            await ctx.send(
                f":white_check_mark: Word Filter: `{channelName}` removed from "
                "the channel allowlist."
            )

    @_channel.command(name="list", aliases=["ls"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _channelList(self, ctx):
        """List channels on the allowlist.
        NOTE: do this in a channel outside of the viewing public
        """
        guildName = ctx.message.guild.name

        channelAllowed = await self.config.guild(ctx.guild).channelAllowed()

        if channelAllowed:
            display = []
            for channel in channelAllowed:
                display.append("`{}`".format(channel))

            page = paginator.Pages(ctx=ctx, entries=display, show_entry_count=True)
            page.embed.title = f"Allowlist channels for: **{guildName}**"
            page.embed.colour = discord.Colour.red()
            await page.paginate()
        else:
            await ctx.send(f"Sorry, there are no channels in the allowlist for **{guildName}**")

    async def checkMessageServerAndChannel(self, msg):
        """Checks to see if the message is in a server/channel eligible for
        filtering.

        Parameters
        ----------
        msg : discord.Message
            The message that we want to check.

        Returns
        -------
        Boolean
            True if the message is eligible for filtering, else False.
        """
        # Filter only configured servers, not private DMs.
        if isinstance(msg.channel, discord.DMChannel):
            return False

        filters = await self.config.guild(msg.guild).filters()

        # Do not filter allowlist channels
        try:
            allowlist = await self.config.guild(msg.guild).channelAllowed()
            for channels in allowlist:
                if channels.lower() == msg.channel.name.lower():
                    return False
        except Exception as error:  # pylint: disable=broad-except
            # Most likely no allowlist channels.
            self.logger.error("Exception occured while checking allowlist channels!")
            self.logger.error(error)

        # Check if mod or admin, and do not filter if togglemod is enabled.
        try:
            toggleMod = await self.config.guild(msg.guild).toggleMod()
            if toggleMod:
                if await self.bot.is_mod(msg.author) or await self.bot.is_admin(msg.author):
                    return False
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error("Exception occurred in checking keyToggleMod!")
            self.logger.error(error)

        return True

    async def containsFilterableWords(self, msg):
        """Checks to see if the message contains words that we need to filter out.
        If the message is in a server/channel that does not exist or is whitelisted,
        this function will return False.

        Parameters
        ---------
        msg : discord.Message
            The message that we want to check.

        Returns
        -------
        Boolean
            True if message contains words that can be filtered, else False.
        """
        if not await self.checkMessageServerAndChannel(msg):
            return False

        filteredMsg = msg.content
        filters = await self.config.guild(msg.guild).filters()
        filteredMsg = _filterWord(filters, filteredMsg)

        if msg.content == filteredMsg:
            return False
        return True

    async def checkWords(
        self, msg, newMsg=None
    ):  # pylint: disable=too-many-locals, too-many-branches
        """This method, given a message, will check to see if the message contains
        any filterable words, and if it does, deletes the original message and
        sends another message with the filterable words censored.

        Parameters:
        -----------
        msg: discord.Message
            The message that was sent, or the message before it was edited.
        newMsg: discord.Message
            The new message after it was edited.

        Returns:
        --------
        Nothing.
        """
        if newMsg and not await self.checkMessageServerAndChannel(newMsg):
            return

        if not await self.checkMessageServerAndChannel(msg):
            return

        blacklistedCmd = False

        filteredWords = await self.config.guild(msg.guild).filters()
        commandDenied = await self.config.guild(msg.guild).commandDenied()

        if newMsg:
            checkMsg = newMsg.content
        else:
            checkMsg = msg.content
        originalMsg = checkMsg
        filteredMsg = originalMsg
        oneWord = _isOneWord(checkMsg)

        for prefix in await self.bot.get_prefix(msg):
            for cmd in commandDenied:
                if checkMsg.startswith(prefix + cmd):
                    blacklistedCmd = True

        try:
            filteredMsg = _filterWord(filteredWords, filteredMsg)
        except re.error as error:  # pylint: disable=broad-except
            self.logger.error("Exception!")
            self.logger.error(error)
            self.logger.info("Filtered message: %s", filteredMsg)

        allFiltered = _isAllFiltered(filteredMsg)

        if filteredMsg == originalMsg:
            return  # no bad words, don't need to do anything else

        await msg.delete()
        if blacklistedCmd:
            # If the it contains a filtered word AND the blacklisted command flag was
            # set above, then:
            # - Delete the message,
            # - Notify on the channel that the message was filtered without showing context
            # - DM user with the filtered context as per what we see usually.
            filterNotify = "{0.author.mention} was filtered!".format(msg)
            notifyMsg = await msg.channel.send(filterNotify)
            filterNotify = "You were filtered! Your message was: \n"
            embed = discord.Embed(
                colour=random.choice(COLOURS),
                description="{0.author.name}#{0.author.discriminator}: "
                "{1}".format(msg, filteredMsg),
            )
            try:
                await msg.author.send(filterNotify, embed=embed)
            except discord.errors.Forbidden as error:
                self.logger.error("Could not DM user, perhaps they have blocked DMs?")
                self.logger.error(error)
            await asyncio.sleep(3)
            await notifyMsg.delete()
        elif (filteredMsg != originalMsg and oneWord) or allFiltered:
            filterNotify = "{0.author.mention} was filtered!".format(msg)
            notifyMsg = await msg.channel.send(filterNotify)
            await asyncio.sleep(3)
            await notifyMsg.delete()
        else:
            filterNotify = "{0.author.mention} was filtered! Message was: \n".format(msg)
            embed = discord.Embed(
                colour=random.choice(COLOURS),
                description="{0.author.name}#{0.author.discriminator}: "
                "{1}".format(msg, filteredMsg),
            )
            await msg.channel.send(filterNotify, embed=embed)

        self.logger.info(
            "Author : %s#%s (%s)", msg.author.name, msg.author.discriminator, msg.author.id
        )
        self.logger.info("Message: %s", originalMsg)

    # Event listeners
    @commands.Cog.listener()
    async def on_message(self, msg):
        await self.checkWords(msg)

    @commands.Cog.listener()
    async def on_message_edit(self, msg, newMsg):
        await self.checkWords(msg, newMsg)


def _censorMatch(matchobj):
    matchLength = len(matchobj.group(0))
    return "`" + ("*" * matchLength) + "`"


def _filterWord(words, string):
    # Combine all filter words into one regex
    numFilters = len(words) - 1
    reFormat = r"\b(?:" + (r"{}|") * numFilters + r"{})\b"
    regex = reFormat.format(*words)

    # Replace the offending string with the correct number of stars.
    return re.sub(regex, _censorMatch, string, flags=re.IGNORECASE)


def _isOneWord(string):
    return len(string.split()) == 1


def _isAllFiltered(string):
    words = string.split()
    cnt = 0
    for word in words:
        if bool(re.search("[*]+", word)):
            cnt += 1
    return cnt == len(words)
