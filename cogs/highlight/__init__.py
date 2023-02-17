"""highlight module.

DM users based on a set of words that they are listening for.
"""

LOG_FOLDER = "log/lui-cogs/highlight/"

import logging
import os
import json
from pathlib import Path

from redbot.core.bot import Red
from .highlight import Highlight

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)


async def setup(bot: Red):
    """Add the cog to the bot."""
    highlightCog = Highlight(bot)
    await bot.add_cog(highlightCog)
