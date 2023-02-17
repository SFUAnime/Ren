from .heist import Heist


async def setup(bot):
    await bot.add_cog(Heist(bot))
