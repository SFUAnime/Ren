"""Catgirl module"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .catgirl import Catgirl

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    nyanko = Catgirl(bot)
    await nyanko.refreshDatabase()
    bot.loop.create_task(nyanko.randomize())
    await bot.add_cog(nyanko)
