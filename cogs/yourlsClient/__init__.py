"""YOURLS module.

"""
from redbot.core.bot import Red
from .yourlsCmd import YOURLS


def setup(bot: Red):
    """Add the cog to the bot."""
    yourlsCog = YOURLS(bot)
    bot.add_cog(yourlsCog)
