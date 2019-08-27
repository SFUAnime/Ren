"""SFU module.

This module handles all things related to Simon Fraser University
"""

import os
from redbot.core.bot import Red
from .courses import SFUCourses
from .roads import SFURoads

def checkFolders():
    """Make sure folder for logs is available."""
    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)

def setup(bot: Red):
    """Add the cog to the bot."""
    checkFolders()
    coursesCog = SFUCourses(bot)
    roadsCog = SFURoads(bot)
    bot.add_cog(coursesCog)
    bot.add_cog(roadsCog)
