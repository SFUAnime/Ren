"""Tags module
Custom commands with ownership, stats, and more.
"""

from redbot.core.bot import Red
from .tags import Tags


def setup(bot: Red):
    CheckForDb()
    """Add the cog to the bot."""
    bot.add_cog(Tags(bot))

def CheckForDb():
    """
    checks if tags.json exists in this folder, otherwise creates it
    """
    try:
        f = open('tags.json')
        f.close()
    except FileNotFoundError:
        f = open('tags.json', "x")
        f.close()