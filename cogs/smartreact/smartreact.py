"""Smartreact, for all your autoreact needs.

This cog was originally from flapjax/FlapJack-Cogs in v2.
"""
import os
import copy
import logging
import re
import asyncio
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.utils import paginator
from redbot.core.bot import Red
from redbot.core.commands.context import Context

UPDATE_WAIT_DUR = 1200  # Autoupdate waits this much before updating

BASE_GUILD = {"emojis": {}}


class SmartReact(commands.Cog):
    """Create automatic reactions when trigger words are typed in chat"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)  # Register default (empty) settings.
        self.update_wait = False  # boolean to check if already waiting

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.SmartReact")
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

    @commands.group(name="react")
    @commands.guild_only()
    # @checks.mod_or_permissions(manage_messages=True)
    async def reacts(self, ctx):
        """Smart Reacts, modified."""
        pass

    @reacts.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def add(self, ctx: Context, word: str, emoji: str):
        """Add an auto reaction to a word.

        Parameters:
        -----------
        word: str
            The word you wish to react to.
        emoji: Union[str, discord.Emoji]
            The emoji you wish to react with, intrepreted as the string representation
            with <:name:id> if it is a custom emoji.
        """
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(ctx, word, emoji)

    @reacts.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def delete(self, ctx: Context, word: str, emoji: str):
        """Delete an auto reaction to a word.

        Parameters:
        -----------
        word: str
            The word you wish to react to.
        emoji: Union[str, discord.Emoji]
            The emoji you wish to react with, intrepreted as the string representation
            with <:name:id> if it is a custom emoji.
        """
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(ctx, word, emoji)

    @reacts.command(name="reload")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def reload(self, ctx):
        """Reloads auto reactions with new emojis by name"""
        code = await self.update_emojis(ctx.guild)
        await ctx.send("Reload success.")

    @reacts.command(name="list", no_pm=True, pass_context=True)
    # @checks.mod_or_permissions(manage_messages=True)
    async def list(self, ctx):
        """List the auto reaction emojis and triggers."""
        display = []
        emojis = await self.config.guild(ctx.guild).emojis()
        for emoji, triggers in emojis.items():
            text = "{}: ".format(emoji)
            for trig in triggers:
                text += "{} ".format(trig)
            display.append(text)

        if not display:
            await ctx.send("There are no smart reacts configured in this server.")
        else:
            page = paginator.Pages(ctx=ctx, entries=display, show_entry_count=True)
            page.embed.title = "Smart React emojis for: **{}**".format(ctx.guild.name)
            page.embed.colour = discord.Colour.red()
            await page.paginate()

    def fix_custom_emoji(self, emoji: str):
        self.logger.debug("Emoji: %s", emoji)
        try:
            if emoji[:2] != "<:":
                return emoji
            self.logger.debug(emoji.split(":")[2][:-1])
            return [
                emote
                for guild in self.bot.guilds
                for emote in guild.emojis
                if emote.id == int(emoji.split(":")[2][:-1])
            ][0]
        except IndexError:
            self.logger.error("Index error as follows", exc_info=True)
            return None

    # From Twentysix26's trigger.py cog
    async def is_command(self, msg):
        """Check to see if a message is a from a command.

        Parameters:
        -----------
        msg: discord.Message
        """
        if callable(self.bot.command_prefix):
            prefixes = await self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    # Helper function that matches the name of the emoji and gets the updated custom emoji ID
    # Will raise ValueError if the comparison emoji is not in the names_list
    def get_updated_emoji(self, nameList, compare_emoji, guild):
        """Get updated emoji ID of a custom emoji.

        Parameters:
        -----------
        nameList: [ str ]
            A list of emoji names to check against. This should be in the same order as
            retrieved from guild.emojis.
        compareEmoji: str
            The emoji that needs to be updated.
        guild: discord.Guild
            The discord guild in question.

        Returns:
        --------
        str
            The string of the emoji.

        Raises:
        -------
        ValueError
            Emoji is not in the nameList
        """
        locv = nameList.index(compare_emoji.split(":")[1].lower())
        self.logger.debug("Updated emoji value: %s", guild.emojis[locv])
        return str(guild.emojis[locv])

    async def update_emojis(self, guild):
        """Update the emojis on the guild.

        Parameters:
        -----------
        guild: discord.Guild
            The guild to update.
        """
        async with self.config.guild(guild).emojis() as emojiList:
            namesList = [x.name.lower() for x in guild.emojis]

            for emoji in emojiList.keys():
                # Update any emojis in the trigger words
                for idx, word in enumerate(emojiList[emoji]):
                    if not ":" in word:  # Hackishly makes sure it's a custom emoji
                        continue

                    try:
                        updated_emoji = self.get_updated_emoji(namesList, word, guild)
                    except ValueError:
                        continue  # Don't care if doesn't exist
                    if word != updated_emoji:
                        emojiList[emoji][idx] = updated_emoji

                if not ":" in emoji:
                    continue

                # Update the emoji key
                try:
                    new_emoji_key = self.get_updated_emoji(namesList, emoji, guild)
                except ValueError:
                    continue  # Don't care if doesn't exist
                if emoji != new_emoji_key:
                    emojiList[new_emoji_key] = emojiList.pop(emoji)
        # self.settings[server.id] = settings

        # dataIO.save_json(self.settings_path, self.settings)

    async def create_smart_reaction(self, ctx: Context, word: str, emoji: str):
        """Add a word to be autoreacted to.

        Parameters:
        -----------
        context: Context
            The context given by discord.py
        word: str
            The word you wish to react to.
        emoji: Union[str, discord.Emoji]
            The emoji you wish to react with.
        """
        try:
            # Use the reaction to see if it's valid
            await ctx.message.add_reaction(emoji)
        except (discord.HTTPException, discord.InvalidArgument):
            await ctx.send("That's not an emoji I recognize.")
            self.logger.error("Could not add reaction.", exc_info=True)
            return

        async with self.config.guild(ctx.guild).emojis() as emojiDict:
            if str(emoji) in emojiDict:
                if word.lower() in emojiDict[str(emoji)]:
                    await ctx.send("This smart reaction already exists.")
                    return
                emojiDict[str(emoji)].append(word.lower())
            else:
                emojiDict[str(emoji)] = [word.lower()]

        await ctx.send("Successfully added this reaction.")

    async def remove_smart_reaction(self, ctx: Context, word: str, emoji: str):
        """Remove a word from being autoreacted to.

        Parameters:
        -----------
        context: Context
            The context given by discord.py
        word: str
            The word you wish to stop reacting to.
        emoji: Union[str, discord.Emoji]
            The emoji you wish to stop reacting with.
        """
        try:
            # Use the reaction to see if it's valid
            await ctx.message.add_reaction(emoji)
        except (discord.HTTPException, discord.InvalidArgument):
            await ctx.send("That's not an emoji I recognize.")
            return

        async with self.config.guild(ctx.guild).emojis() as emojiDict:
            if str(emoji) in emojiDict:
                if word.lower() in emojiDict[str(emoji)]:
                    emojiDict[str(emoji)].remove(word.lower())
                    if not emojiDict[str(emoji)]:
                        emojiDict.pop(str(emoji))
                    await ctx.send("Removed this smart reaction.")
                else:
                    await ctx.send("That emoji is not used as a reaction " "for that word.")
            else:
                await ctx.send("There are no smart reactions which use " "this emoji.")

    @commands.Cog.listener("on_guild_emojis_update")
    async def emojis_update_listener(self, guild: discord.Guild, before, after):
        if not self.update_wait:
            try:
                self.update_wait = True
                # Requires the server to have at least one emoji
                if not guild.emojis:
                    return
                # Wait for some time for further changes before updating
                self.logger.info("SmartReact update wait started for guild %s", guild.name)
                await asyncio.sleep(UPDATE_WAIT_DUR)
                await self.update_emojis(guild)
                self.logger.info("SmartReact update successful for guild %s", guild.name)
            except Exception as error:
                self.logger.error("SmartReact error: %s", error, exc_info=True)
            self.update_wait = False

    # Special thanks to irdumb#1229 on discord for helping me make this method
    # "more Pythonic"
    @commands.Cog.listener("on_message")
    async def msgListener(self, message):
        if message.author == self.bot.user:
            return
        if await self.is_command(message):
            return
        if not message.guild:
            return
        react_dict = await self.config.guild(message.guild).emojis()

        # For matching non-word characters and emojis
        end_sym = r"([\W:\\<>._]+|$)"
        st_sym = r"([\W:\\<>._]+|^)"
        for emoji in react_dict:
            if any(
                re.search(st_sym + w + end_sym, message.content, re.IGNORECASE)
                for w in react_dict[emoji]
            ):
                fixed_emoji = self.fix_custom_emoji(emoji)
                if fixed_emoji:
                    try:
                        await message.add_reaction(fixed_emoji)
                    except discord.Forbidden as e:
                        pass
