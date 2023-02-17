from typing import List

from .constants import COLOUR_BLURPLE, MAX_MSG_LEN
from .data import TagAlias, TagInfo

import discord
from redbot.core.utils import AsyncIter, chat_formatting


def checkLengthInRaw(content: str) -> bool:
    """Checks if the length of the specified content with markdown escaped
    exceeds Discord's max message length or not.

    Returns
    -------
    bool
        False if the content length exceeds Discord's max message length
        when all markdown characters are escape, and True otherwise.
    """
    return len(discord.utils.escape_markdown(content)) <= MAX_MSG_LEN


async def createSimplePages(
    items: List[str], embedTitle: str = "", embedAuthor: discord.Member = None
):
    """Create embed pages for the redbot menu coroutine.

    It features the following:
    - Each entry is numbered.
    - The total number of items is visible.
    - The total number of pages is visible.

    Parameters
    ----------
    items: List[ str ]
        A list of strings you wish to display to the user.
    embedTitle: Optional[ str ]
        The title for all the embed pages
    embedAuthor: Optional[ discord.Member ]
        The author. If passed in, it will set the footer author's name and
        avatar

    Returns
    -------
    List[ discord.Embed ]
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
                icon_url=embedAuthor.display_avatar.url,
            )
        pageList.append(embed)

    return pageList


def tagDecoder(obj):
    if "__tag__" in obj:
        return TagInfo(**obj)
    if "__tag_alias__" in obj:
        return TagAlias(**obj)
    return obj
