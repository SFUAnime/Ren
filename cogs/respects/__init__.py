"""respects module.

Press f to pay respects
"""

from redbot.core.bot import Red
from .respects import Respects


def setup(bot: Red):
    """Add the cog to the bot."""
    customCog = Respects(bot)
    bot.add_cog(customCog)
