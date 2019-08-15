"""SFU module.

This module handles all things related to Simon Fraser University
"""

LOG_FOLDER = "log/lui-cogs/sfu/"

# import logging
import os

from redbot.core.bot import Red
from .courses import SFUCourses

def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)

def setup(bot: Red):
    """Add the cog to the bot."""
    global LOGGER # pylint: disable=global-statement
    checkFolders()
    coursesCog = SFUCourses(bot)
    # sfuCog.logger = logging.getLogger("red.SFU")
    # if sfuCog.logger.level == 0:
    #     # Prevents the LOGGER from being loaded again in case of module reload.
    #     sfuCog.logger.setLevel(logging.DEBUG)
    #     handler = logging.FileHandler(filename="{}info.log".format(LOG_FOLDER),
    #                                   encoding="utf-8",
    #                                   mode="a")
    #     handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
    #                                            datefmt="[%d/%m/%Y %H:%M:%S]"))
    #     sfuCog.logger.addHandler(handler)
    bot.add_cog(coursesCog)
