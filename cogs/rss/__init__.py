"""
Init file for RSS cog.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .rss import RSSFeed

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    rssCog = RSSFeed(bot)
    await bot.add_cog(rssCog)
    bot.loop.create_task(rssCog.rss())
