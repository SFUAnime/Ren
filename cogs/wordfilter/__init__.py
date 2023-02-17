"""wordfilter module.

To filter words in a more smart/useful way than simply detecting and
deleting a message.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .wordfilter import WordFilter

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    wordFilterCog = WordFilter(bot)
    await bot.add_cog(wordFilterCog)
