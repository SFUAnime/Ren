"""Catgirl module"""
from redbot.core.bot import Red
from .catgirl import Catgirl


async def setup(bot: Red):
    """Add the cog to the bot."""
    nyanko = Catgirl(bot)
    await nyanko.refreshDatabase()
    bot.loop.create_task(nyanko.randomize())
    bot.add_cog(nyanko)
