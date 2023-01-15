"""slashsync module.

Sync slash commands from the bot to the server.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .slashsync import SlashSync

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(SlashSync(bot))
