"""Ranks cog.
Keep track of active members on the server.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .ranks import Ranks

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(Ranks(bot))
