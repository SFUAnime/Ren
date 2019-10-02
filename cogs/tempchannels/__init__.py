"""tempchannels module.

DM users based on a set of words that they are listening for.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

LOG_FOLDER = "log/lui-cogs/tempchannels/"

import logging
import os

from redbot.core.bot import Red
from .tempchannels import TempChannels

def setup(bot: Red):
    """Add the cog to the bot."""
    tempchannelsCog = TempChannels(bot)
    bot.add_cog(tempchannelsCog)
