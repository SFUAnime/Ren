"""Triggered cog
`triggered from spoopy.
"""

import os
import discord
import urllib.request
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from PIL import Image, ImageChops, ImageOps

SAVE_FOLDER = "data/lui-cogs/triggered/" # Path to save folder.
SAVE_FILE = "settings.json"
AVATAR_URL = "https://images.discordapp.net/avatars/{0.id}/{0.avatar}.png?size=1024"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

class Triggered: # pylint: disable=too-many-instance-attributes
    """We triggered, fam."""


    # Class constructor
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="triggered", pass_context=True)
    async def triggered(self, ctx):
        """Are you triggered? Say no more."""
        savePath = await self._createTrigger(ctx.message.author)
        if not savePath:
            return
        await self.bot.send_file(ctx.message.channel, savePath),


    async def _createTrigger(self, user):
        """Fetches the user's avatar, and creates a triggered GIF

        Parameters:
        -----------
        user: discord.User

        Returns:
        --------
        savePath: str, or None
        """
        path = "{}{}.png".format(SAVE_FOLDER, user.id)
        savePath = "{}{}-trig.gif".format(SAVE_FOLDER, user.id)
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [("User-agent", "Mozilla/5.0")]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(user.avatar_url, path)
        except Exception as error:
            print(user.avatar_url)
            print(error)
        avatar = Image.open(path)
        if not avatar:
            return
        OFFSET = 30
        topRight = ImageChops.offset(avatar, -OFFSET, OFFSET)
        topLeft = ImageChops.offset(avatar, -OFFSET, -OFFSET+6)
        botRight = ImageChops.offset(avatar, OFFSET-5, OFFSET-15)
        botLeft = ImageChops.offset(avatar, -OFFSET+15, OFFSET-10)

        topRight = ImageOps.crop(topRight, OFFSET)
        botRight = ImageOps.crop(botRight, OFFSET)
        avatar = ImageOps.crop(avatar, OFFSET)
        topLeft = ImageOps.crop(topLeft, OFFSET)
        botLeft = ImageOps.crop(botLeft, OFFSET)
        topRight.save(savePath, format="GIF",
                      append_images=[botLeft, botRight, topLeft, avatar],
                      save_all=True,
                      duration=30,
                      loop=0)
        return savePath



def setup(bot):
    """Add the cog to the bot."""
    checkFolder()
    customCog = Triggered(bot)
    bot.add_cog(customCog)
