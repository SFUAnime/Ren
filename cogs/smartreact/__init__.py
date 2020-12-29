"""The smart reaction module.

This cog requires paginator.py, obtainable from Rapptz/RoboDanny.
"""

from redbot.core.bot import Red
from .smartreact import SmartReact


def setup(bot: Red):
    bot.add_cog(SmartReact(bot))
