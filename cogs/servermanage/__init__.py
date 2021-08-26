"""servermanage module.

Auto-assign server banner and icons on particular days.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

from redbot.core.bot import Red
from .servermanage import ServerManage


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(ServerManage(bot))
