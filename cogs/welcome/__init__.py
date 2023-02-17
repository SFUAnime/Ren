"""Welcome module
Sends welcome DMs to users that join the server.
"""
import json
from pathlib import Path

LOG_FOLDER = "log/lui-cogs/welcome/"

from redbot.core.bot import Red
from .welcome import Welcome

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(Welcome(bot))
