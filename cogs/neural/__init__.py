import json
from pathlib import Path

from redbot.core.bot import Red

from .neural import Neural

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__: str = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    """Add the cog to the bot."""
    await bot.add_cog(Neural(bot))
