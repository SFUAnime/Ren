"""Respects cog
A replica of +f seen in another bot, except smarter..
"""

import discord
from discord.ext import commands

class Respects:
    """Pay your respects."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="f", pass_context=True, no_pm=True) 
    async def payRespects(self, ctx):
        """Pay your respects."""
        pass

def setup(bot):
    """Add the cog to the bot."""
    customCog = Respects(bot)
    bot.add_cog(customCog)
