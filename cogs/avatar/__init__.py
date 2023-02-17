"""avatar module.

Saves avatar images of users when they update them.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .avatar import Avatar

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(Avatar(bot))
