import enum
from enum import Enum
import io
import logging

import discord
from PIL import Image, ImageChops, ImageOps, ImageEnhance

from redbot.core import data_manager
from redbot.core.bot import Red

AVATAR_FILE_NAME = "{0.id}-triggered.gif"


class Modes(Enum):
    TRIGGERED = enum.auto()
    REALLY_TRIGGERED = enum.auto()
    HYPER_TRIGGERED = enum.auto()


class Core:
    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.luicogs.Triggered")
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)
        # We need a custom header or else we get a HTTP 403 Unauthorized
        self.headers = {"User-agent": "Mozilla/5.0"}

    async def _createTrigger(self, user: discord.User, mode=Modes.TRIGGERED):
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
            if mode == Modes.REALLY_TRIGGERED:
                red_overlay = Image.new(mode="RGBA", size=avatar.size, color=(255, 0, 0, 255))
                mask = Image.new(mode="RGBA", size=avatar.size, color=(255, 255, 255, 127))
                avatar = Image.composite(avatar, red_overlay, mask)

            elif mode == Modes.HYPER_TRIGGERED:
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
