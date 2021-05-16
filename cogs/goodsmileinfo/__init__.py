"""Good Smile Info module
Parse GSC info
"""

from redbot.core.bot import Red
from .gscinfo import GoodSmileInfo


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(GoodSmileInfo(bot))
