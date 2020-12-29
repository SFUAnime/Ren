"""birthday module.

Auto-add guild members to a birthday role on their birthday.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

from redbot.core.bot import Red
from .birthday import Birthday


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Birthday(bot))
