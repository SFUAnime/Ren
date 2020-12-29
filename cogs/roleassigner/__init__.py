"""roleassigner module.

Assign roles to certain guild members.
"""

from redbot.core.bot import Red
from .roleassigner import RoleAssigner


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(RoleAssigner(bot))
