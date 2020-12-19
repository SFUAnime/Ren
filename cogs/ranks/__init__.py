"""Ranks cog.
Keep track of active members on the server.
"""

from redbot.core.bot import Red
from .ranks import Ranks


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Ranks(bot))
