"""Triggered cog
`triggered from spoopy.
"""

import os
import urllib.request
import discord
from discord.ext import commands
from PIL import Image, ImageChops, ImageOps

SAVE_FOLDER = "data/lui-cogs/triggered/" # Path to save folder.
SAVE_FILE = "settings.json"
AVATAR_URL = "https://cdn.discordapp.com/avatars/{0.id}/{0.avatar}.png?size=512"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

class Triggered: # pylint: disable=too-few-public-methods
    """We triggered, fam."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="triggered", pass_context=True)
    async def triggered(self, ctx, user: discord.Member = None):
        """Are you triggered? Say no more."""
        if not user:
            user = ctx.message.author
        await self.bot.send_typing(ctx.message.channel)
        savePath = await self._createTrigger(user)
        if not savePath:
            await self.bot.say("Something went wrong, try again.")
            return
        await self.bot.send_file(ctx.message.channel, savePath)

    async def _createTrigger(self, user):
        """Fetches the user's avatar, and creates a triggered GIF

        Parameters:
        -----------
        user: discord.Member

        Returns:
        --------
        savePath: str, or None
        """
        path = "{}{}.png".format(SAVE_FOLDER, user.id)
        savePath = "{}{}-trig.gif".format(SAVE_FOLDER, user.id)

        opener = urllib.request.build_opener()
        # We need a custom header or else we get a HTTP 403 Unauthorized
        opener.addheaders = [("User-agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        try:
            urllib.request.urlretrieve(AVATAR_URL.format(user), path)
        except urllib.request.ContentTooShortError:
            return None
        except urllib.error.HTTPError:
            # Use the default.
            urllib.request.urlretrieve(user.default_avatar_url, path)

        avatar = Image.open(path)

        if not avatar:
            return

        offsets = [(15, 15), (5, 10), (-15, -15),
                   (10, -10), (10, 0), (-15, 10),
                   (10, -5)]
        images = []

        for xcoord, ycoord in offsets:
            image = ImageChops.offset(avatar, xcoord, ycoord)
            image = ImageOps.crop(image, 15)
            images.append(image)
        avatar = ImageOps.crop(avatar, 15)
        avatar.save(savePath, format="GIF",
                    append_images=images,
                    save_all=True,
                    duration=25,
                    loop=0)
        return savePath



def setup(bot):
    """Add the cog to the bot."""
    checkFolder()
    customCog = Triggered(bot)
    bot.add_cog(customCog)
