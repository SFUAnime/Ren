from .invoice import InVoice


async def setup(bot):
    await bot.add_cog(InVoice())
