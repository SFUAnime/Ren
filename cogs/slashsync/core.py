import logging

from redbot.core.bot import Red


class Core:
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
