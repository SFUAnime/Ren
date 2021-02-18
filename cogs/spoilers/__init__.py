"""Spoilers module

Reaction-based spoilers before Discord implemented spoilers.
"""

from redbot.core.bot import Red
from .spoilers import Spoilers


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Spoilers(bot))
