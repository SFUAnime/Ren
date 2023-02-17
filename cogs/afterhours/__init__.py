"""afterhours module.

All the special casing bs we need to do for this channel.
"""

import json
from pathlib import Path

from redbot.core.bot import Red
from .afterhours import AfterHours

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red):
    """Add the cog to the bot."""
    ahCog = AfterHours(bot)
    await bot.add_cog(ahCog)
