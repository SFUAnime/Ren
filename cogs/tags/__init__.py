"""Tags module
Custom commands with ownership, stats, and more.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .tags import Tags

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(Tags(bot))
