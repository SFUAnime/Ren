from .constants import COLOUR_BLURPLE
from .data import TagAlias, TagInfo

import discord
from redbot.core.utils import AsyncIter, chat_formatting


async def createSimplePages(
    items: [str], embedTitle: str = "", embedAuthor: discord.Member = None
):
    """Create embed pages for the redbot menu coroutine.

    It features the following:
    - Each entry is numbered.
    - The total number of items is visible.
    - The total number of pages is visible.

    Parameters
    ----------
    items: [ str ]
        A list of strings you wish to display to the user.
    embedTitle: Optional[ str ]
        The title for all the embed pages
    embedAuthor : Optional[ discord.Member ]
        The author. If passed in, it will set the footer author's name and
        avatar

    Returns
    -------
    [ discord.Embed ]
        A list of `discord.Embed`s, which can be passed directly into Red's
        menu coroutine.
    """
    if embedAuthor and not isinstance(embedAuthor, discord.Member):
        raise RuntimeError("Please pass in a discord.Member object")
    display = []
    pageList = []
    for num, theItem in enumerate(items, start=1):
        display.append(f"{num}. {theItem}")
    msg = "\n".join(display)
    pages = list(chat_formatting.pagify(msg, page_length=300))
    totalPages = len(pages)
    totalEntries = len(display)

    async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
        embed = discord.Embed(title=embedTitle, description=page)
        embed.set_footer(text=f"Page {pageNumber}/{totalPages} ({totalEntries} entries)")
        embed.colour = COLOUR_BLURPLE
        if embedAuthor:
            embed.set_author(
                name=embedAuthor.display_name,
                icon_url=embedAuthor.avatar_url or embedAuthor.default_avatar_url,
            )
        pageList.append(embed)

    return pageList


def tagDecoder(obj):
    if "__tag__" in obj:
        return TagInfo(**obj)
    if "__tag_alias__" in obj:
        return TagAlias(**obj)
    return obj
