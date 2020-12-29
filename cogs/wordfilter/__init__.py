"""wordfilter module.

To filter words in a more smart/useful way than simply detecting and
deleting a message.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

from redbot.core.bot import Red
from .wordfilter import WordFilter


def setup(bot: Red):
    """Add the cog to the bot."""
    wordFilterCog = WordFilter(bot)
    bot.add_cog(wordFilterCog)
