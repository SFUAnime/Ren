"""Heartbeat module
Sends a push ping to a third-party site like StatusCake to check uptime.
"""

from redbot.core.bot import Red
from .heartbeat import Heartbeat


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Heartbeat(bot))
