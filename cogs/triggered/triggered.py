"""Triggered cog
`triggered from spoopy.
"""

import os
import urllib.request
import discord
from redbot.core import commands, data_manager
from PIL import Image, ImageChops, ImageOps, ImageFilter, ImageEnhance
from enum import Enum

Modes = Enum("Modes", "triggered reallytriggered hypertriggered")

AVATAR_URL = "https://cdn.discordapp.com/avatars/{0.id}/{0.avatar}.png?size=512"


class Triggered(commands.Cog):
    """We triggered, fam."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)

    @commands.command(name="triggered")
    async def triggered(self, ctx, user: discord.Member = None):
        """Are you triggered? Say no more."""
        if not user:
            user = ctx.message.author
        async with ctx.typing():
            # bot is typing here...
            savePath = await self._createTrigger(user, mode=Modes.triggered)
            if not savePath:
                await self.bot.say("Something went wrong, try again.")
                return
            await ctx.send(file=discord.File(savePath))

    @commands.command(name="reallytriggered")
    async def hypertriggered(self, ctx, user: discord.Member = None):
        """Are you in an elevated state of triggered? Say no more."""
        if not user:
            user = ctx.message.author
        async with ctx.typing():
            # bot is typing here...
            savePath = await self._createTrigger(user, mode=Modes.reallytriggered)
            if not savePath:
                await self.bot.say("Something went wrong, try again.")
                return
            await ctx.send(file=discord.File(savePath))

    @commands.command(name="hypertriggered")
    async def deepfry(self, ctx, user: discord.Member = None):
        """Are you incredibly triggered? Say no more."""
        if not user:
            user = ctx.message.author
        async with ctx.typing():
            # bot is typing here...
            savePath = await self._createTrigger(user, mode=Modes.hypertriggered)
            if not savePath:
                await self.bot.say("Something went wrong, try again.")
                return
            await ctx.send(file=discord.File(savePath))

    async def _createTrigger(self, user, mode=Modes.triggered):
        """Fetches the user's avatar, and creates a triggered GIF, applies additional PIL image transformations based on specified mode
        Parameters:
        -----------
        user: discord.Member
        mode: Mode

        Returns:
        --------
        savePath: str, or None
        """
        path = os.path.join(self.saveFolder, "{}.png".format(user.id))
        savePath = os.path.join(self.saveFolder, "{}-trig.gif".format(user.id))

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

        offsets = [(15, 15), (5, 10), (-15, -15), (10, -10), (10, 0), (-15, 10), (10, -5)]
        images = []

        # if hyper mode is set
        if mode == Modes.reallytriggered:
            red_overlay = Image.new(mode="RGBA", size=avatar.size, color=(255, 0, 0, 255))
            mask = Image.new(mode="RGBA", size=avatar.size, color=(255, 255, 255, 127))
            avatar = Image.composite(avatar, red_overlay, mask)

        elif mode == Modes.hypertriggered:
            avatar = ImageEnhance.Color(avatar).enhance(5)
            avatar = ImageEnhance.Sharpness(avatar).enhance(24)
            avatar = ImageEnhance.Contrast(avatar).enhance(4)

        for xcoord, ycoord in offsets:
            image = ImageChops.offset(avatar, xcoord, ycoord)
            image = ImageOps.crop(image, 15)
            images.append(image)
        avatar = ImageOps.crop(avatar, 15)

        avatar.save(
            savePath, format="GIF", append_images=images, save_all=True, duration=25, loop=0
        )
        return savePath
