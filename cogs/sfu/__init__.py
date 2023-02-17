"""SFU module.

This module handles all things related to Simon Fraser University
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .sfu import SFU

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(SFU(bot))
