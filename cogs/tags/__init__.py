"""Tags module
Custom commands with ownership, stats, and more.
"""

from redbot.core.bot import Red
from .tags import Tags


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Tags(bot))
