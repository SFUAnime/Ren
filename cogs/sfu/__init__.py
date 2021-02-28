"""SFU module.

This module handles all things related to Simon Fraser University
"""

from redbot.core.bot import Red
from .sfu import SFU


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(SFU(bot))
