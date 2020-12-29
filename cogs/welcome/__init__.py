"""Welcome module
Sends welcome DMs to users that join the server.
"""

LOG_FOLDER = "log/lui-cogs/welcome/"

from redbot.core.bot import Red
from .welcome import Welcome


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Welcome(bot))
