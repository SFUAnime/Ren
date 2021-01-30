from .triggered import Triggered


def setup(bot):
    bot.add_cog(Triggered(bot))
