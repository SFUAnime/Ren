"""highlight module.

DM users based on a set of words that they are listening for.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

LOG_FOLDER = "log/lui-cogs/highlight/"

import logging
import os

from redbot.core.bot import Red
from .highlight import Highlight


def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)


def setup(bot: Red):
    """Add the cog to the bot."""
    highlightCog = Highlight(bot)
    bot.add_cog(highlightCog)
