"""respects module.

Press f to pay respects
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .respects import Respects

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    customCog = Respects(bot)
    await bot.add_cog(customCog)
