from .source import Source
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(Source(bot))
