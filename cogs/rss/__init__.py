"""
Init file for RSS cog.
"""

from redbot.core.bot import Red
from .rss import RSSFeed


def setup(bot: Red):
    """Add the cog to the bot."""
    rssCog = RSSFeed(bot)
    bot.add_cog(rssCog)
    bot.loop.create_task(rssCog.rss())
