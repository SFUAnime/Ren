"""tempchannels module.

Creates a temporary channel.
"""

from redbot.core.bot import Red
from .tempchannels import TempChannels


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(TempChannels(bot))
