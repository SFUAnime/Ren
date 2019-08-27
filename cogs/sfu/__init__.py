"""SFU module.

This module handles all things related to Simon Fraser University
"""

import os
from redbot.core.bot import Red
from .courses import SFUCourses
from .roads import SFURoads


def setup(bot: Red):
    """Add the cog to the bot."""
    coursesCog = SFUCourses(bot)
    roadsCog = SFURoads(bot)
    bot.add_cog(coursesCog)
    bot.add_cog(roadsCog)
