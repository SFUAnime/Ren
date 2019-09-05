"""Smartreact, for all your autoreact needs.

This cog was originally from flapjax/FlapJack-Cogs in v2.
"""
import os
import copy
import re
import asyncio
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils import paginator
from redbot.core.bot import Red

UPDATE_WAIT_DUR = 1200 # Autoupdate waits this much before updating

BASE_GUILD = \
{
    "emojis": {}
}

class SmartReact(commands.Cog):
    """Create automatic reactions when trigger words are typed in chat"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self,
                                      identifier=5842647,
                                      force_registration=True)
        self.config.register_guild(**BASE_GUILD) # Register default (empty) settings.
        self.update_wait = False # boolean to check if already waiting

    @commands.group(name="react")
    @commands.guild_only()
    # @checks.mod_or_permissions(manage_messages=True)
    async def reacts(self, ctx):
        """Smart Reacts, modified."""
        pass

    @reacts.command(name="add")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def add(self, ctx: Context, word: str, emoji: discord.Emoji):
        """Add an auto reaction to a word"""
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(ctx, word, emoji)

    @reacts.command(name="del", aliases=["delete", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def delete(self, ctx: Context, word: str, emoji: discord.Emoji):
        """Delete an auto reaction to a word"""
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(ctx, word, emoji)

    @reacts.command(name="reload", no_pm=True, pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def reload(self, ctx):
        """Reloads auto reactions with new emojis by name"""
        server = ctx.message.server
        code = await self.update_emojis(server)
        await self.bot.say("Reload success.")

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


    def add_default_settings(self, server_id):
        self.settings[server_id] = {}
        dataIO.save_json(self.settings_path, self.settings)

    def fix_custom_emoji(self, emoji):
        try:
            if emoji[:2] != "<:":
                return emoji
            return [r for server in self.bot.servers for r in server.emojis if r.id == emoji.split(':')[2][:-1]][0]
        except IndexError:
            return None

    # From Twentysix26's trigger.py cog
    def is_command(self, msg):
        if callable(self.bot.command_prefix):
            prefixes = self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    # Helper function that matches the name of the emoji and gets the updated custom emoji ID
    # Will raise ValueError if the comparison emoji is not in the names_list
    def get_updated_emoji(self, names_list, compare_emoji, server):
        locv = names_list.index(compare_emoji.split(':')[1].lower())
        return str(server.emojis[locv])
        

    async def update_emojis(self, server):
        names_list = [x.name.lower() for x in server.emojis]
        settings = copy.deepcopy(self.settings[server.id])

        for emoji in self.settings[server.id].keys():
            # Update any emojis in the trigger words
            for idx, w in enumerate(self.settings[server.id][emoji]):
                if not ':' in w: # Hackishly makes sure it's a custom emoji
                    continue

                try:
                    updated_emoji = self.get_updated_emoji(names_list, w, server)
                except ValueError:
                    continue # Don't care if doesn't exist
                if w != updated_emoji:
                    settings[emoji][idx] = updated_emoji

            if not ':' in emoji:
                continue

            # Update the emoji key
            try:
                new_emoji_key = self.get_updated_emoji(names_list, emoji, server)
            except ValueError:
                continue # Don't care if doesn't exist
            if emoji != new_emoji_key:
                settings[new_emoji_key] = settings.pop(emoji)
        self.settings[server.id] = settings

        dataIO.save_json(self.settings_path, self.settings)

    async def create_smart_reaction(self, ctx: Context, word: str, emoji: discord.Emoji):
        """Add a word to be autoreacted to.

        Parameters:
        -----------
        context: Context
            The context given by discord.py
        word: str
            The word you wish to react to.
        emoji: discord.Emoji
            The emoji you wish to react with.
        """
        try:
            # Use the reaction to see if it's valid
            await ctx.add_reaction(emoji)
        except (discord.HTTPException, discord.InvalidArgument):
            await ctx.send("That's not an emoji I recognize.")
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

    async def remove_smart_reaction(self, ctx: Context, word: str, emoji: discord.Emoji):
        """Remove a word from being autoreacted to.

        Parameters:
        -----------
        context: Context
            The context given by discord.py
        word: str
            The word you wish to stop reacting to.
        emoji: discord.Emoji
            The emoji you wish to stop reacting with.
        """
        try:
            # Use the reaction to see if it's valid
            await ctx.add_reaction(emoji)
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
                    await ctx.send("That emoji is not used as a reaction "
                                   "for that word.")
            else:
                await ctx.send("There are no smart reactions which use "
                               "this emoji.")

    @commands.Cog.listener("on_guild_emojis_update")
    async def emojis_update_listener(self, guild: discord.Guild, before, after):
        if not self.update_wait:
            try:
                self.update_wait = True
                # Requires the server to have at least one emoji
                if not guild.emojis:
                    return
                # Wait for some time for further changes before updating
                print("SmartReact update wait started for Server " + str(guild.name))
                await asyncio.sleep(UPDATE_WAIT_DUR)
                await self.update_emojis(guild)
                print("SmartReact update successful for Server " + str(guild.name))
            except Exception as e:
                print("SmartReact error: ")
                print(e)
            self.update_wait = False

    # Special thanks to irdumb#1229 on discord for helping me make this method
    # "more Pythonic"
    @commands.Cog.listener("on_message")
    async def msgListener(self, message):
        if message.author == self.bot.user:
            return
        if self.is_command(message):
            return
        if not message.guild:
            return
        react_dict = await self.config.guild(message.guild).emojis()

        # For matching non-word characters and emojis
        end_sym = r'([\W:\\<>._]+|$)'
        st_sym = r'([\W:\\<>._]+|^)'
        for emoji in react_dict:
            if any(re.search(st_sym + w + end_sym, message.content, re.IGNORECASE) for w in react_dict[emoji]):
                fixed_emoji = self.fix_custom_emoji(emoji)
                if fixed_emoji:
                    try:
                        await self.bot.add_reaction(message, fixed_emoji)
                    except discord.Forbidden as e:
                        pass

def check_folders():
    folder = "data/smartreact"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/smartreact/settings.json"):
        print("Creating default smartreact settings.json...")
        dataIO.save_json("data/smartreact/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = SmartReact(bot)
    bot.add_cog(n)
    bot.add_listener(n.msg_listener, "on_message")
    bot.add_listener(n.emojis_update_listener, "on_server_emojis_update")
