"""wordfilter module.

To filter words in a more smart/useful way than simply detecting and
deleting a message.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

LOG_FOLDER = "log/lui-cogs/wordfilter/"

import logging
import os

from redbot.core.bot import Red
from .wordfilter import WordFilter

def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)

def setup(bot: Red):
    """Add the cog to the bot."""
    global LOGGER # pylint: disable=global-statement
    checkFolders()
    wordFilterCog = WordFilter(bot)
    wordFilterCog.logger = logging.getLogger("red.WordFilter")
    if wordFilterCog.logger.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        wordFilterCog.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="{}info.log".format(LOG_FOLDER),
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        wordFilterCog.logger.addHandler(handler)
    bot.add_cog(wordFilterCog)
