"""Triggered cog
`triggered from spoopy.
"""

import logging
import io
import aiohttp
import discord
from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands import Context
from PIL import Image, ImageChops, ImageOps, ImageFilter, ImageEnhance
from enum import Enum

Modes = Enum("Modes", "triggered reallytriggered hypertriggered")

AVATAR_URL = "https://cdn.discordapp.com/avatars/{0.id}/{0.avatar}.png?size=512"
AVATAR_FILE_NAME = "{0.id}-triggered.gif"


class Triggered(commands.Cog):
    """We triggered, fam."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.luicogs.Triggered")
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)
        # We need a custom header or else we get a HTTP 403 Unauthorized
        self.headers = {"User-agent": "Mozilla/5.0"}

    @commands.hybrid_command(name="triggered")
    async def triggered(self, ctx: Context, user: discord.Member = None):
        """Are you triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.triggered)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))

    @commands.hybrid_command(name="reallytriggered")
    async def hypertriggered(self, ctx: Context, user: discord.Member = None):
        """Are you in an elevated state of triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.reallytriggered)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))

    @commands.hybrid_command(name="hypertriggered")
    async def deepfry(self, ctx: Context, user: discord.Member = None):
        """Are you incredibly triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.hypertriggered)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))

    async def _createTrigger(self, user: discord.User, mode=Modes.triggered):
        """Fetches the user's avatar, and creates a triggered GIF, applies additional PIL image transformations based on specified mode

        Parameters:
        -----------
        user: discord.User
        mode: Modes

        Returns:
        --------
        An io.BytesIO object containing the data for the generated trigger image
        """
        avatarData: bytes

        avatar = user.display_avatar.with_size(512)
        avatarData = await avatar.read()

        if not avatarData:
            self.logger.error("No avatar data received!")
            return

        with Image.open(io.BytesIO(avatarData)) as avatar:

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

            result = io.BytesIO()
            avatar.save(
                result, format="GIF", append_images=images, save_all=True, duration=25, loop=0
            )

            # IMPORTANT: rewind to beginning of the stream before returning
            result.seek(0)

            return result
