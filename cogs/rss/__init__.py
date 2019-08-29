"""
Init file for RSS cog.
"""


import logging
import os

from redbot.core.bot import Red
from .rss import RSSFeed

LOG_FOLDER = "log/lui-cogs/rss"
LOGGER = None
def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)

def setup(bot: Red):
    """Add the cog to the bot."""
    global LOGGER # pylint: disable=global-statement
    LOGGER = logging.getLogger("red.RSSFeed")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="data/rss/info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    rssCog = RSSFeed(bot)
    rssCog.logger = LOGGER
    bot.add_cog(rssCog)
    bot.loop.create_task(rssCog.rss())
