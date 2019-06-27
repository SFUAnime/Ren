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
    global LOGGER # pylint: disable=global-statement
    checkFolders()
    highlightCog = Highlight(bot)
    highlightCog.logger = logging.getLogger("red.Highlight")
    if highlightCog.logger.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        highlightCog.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="{}info.log".format(LOG_FOLDER),
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        highlightCog.logger.addHandler(handler)
    bot.add_cog(highlightCog)
