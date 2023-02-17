"""qrchecker module.

Checks QR code images.

"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .qrchecker import QRChecker

with open(Path(__file__).parent / "info.json", encoding="utf-8") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    await bot.add_cog(QRChecker(bot))
