"""afterhours module.

All the special casing bs we need to do for this channel.
"""

from redbot.core.bot import Red
from .afterhours import AfterHours


def setup(bot: Red):
    """Add the cog to the bot."""
    ahCog = AfterHours(bot)
    bot.add_cog(ahCog)
