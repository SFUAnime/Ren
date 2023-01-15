"""SlashSync

Sync slash commands from the bot to the server.
"""
import logging

from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import info, success


class SlashSync(commands.Cog):
    """Synchronize slash commands on the bot to Discord"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.luicogs.SlashSync")
        self.bgTask = self.bot.loop.create_task(self.waitUntilBotReady())

    async def waitUntilBotReady(self):
        self.logger.debug("Waiting for bot to be ready")
        await self.bot.wait_until_red_ready()
        self.logger.debug("Bot is ready, synchronizing command tree")
        await self.bot.tree.sync()
        self.logger.debug("Command tree synchronized")

    def cog_unload(self):
        self.logger.debug("Clean up background task")
        self.bgTask.cancel()

    @commands.command(name="sync")
    @checks.is_owner()
    async def sync(self, ctx: Context):
        """Synchronize slash commands to Discord"""
        msg = await ctx.send(info("Syncing slash commands to Discord, please wait..."))
        await self.bot.tree.sync()
        await msg.edit(content=success("Synchronized slash commands to Discord."))
