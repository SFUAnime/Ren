from redbot.core.bot import Red
from .catgirl import Catgirl


def setup(bot: Red):
    bot.add_cog(Catgirl(bot))
