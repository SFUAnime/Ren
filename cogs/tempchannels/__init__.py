"""tempchannels module.

DM users based on a set of words that they are listening for.
"""

from redbot.core.bot import Red
from .tempchannels import TempChannels


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(TempChannels(bot))
