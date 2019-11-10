"""avatar module.

Saves avatar images of users when they update them.
"""

from redbot.core.bot import Red
from .avatar import Avatar


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Avatar(bot))
