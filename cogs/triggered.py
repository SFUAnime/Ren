"""Triggered cog
`triggered from spoopy.
"""

import os
import discord
from discord.ext import commands

class Triggered: # pylint: disable=too-many-instance-attributes
    """We triggered, fam."""


    # Class constructor
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="triggered", pass_context=True)
    async def triggered(self, ctx):
        pass


def setup(bot):
    """Add the cog to the bot."""
    customCog = Triggered(bot)
    bot.add_cog(customCog)
