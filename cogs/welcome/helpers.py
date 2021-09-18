import discord
from typing import Dict, List

from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box


async def createTagListPages(
    descDict: Dict[str, str], embedTitle: str = "", embedAuthor: discord.Member = None
) -> List[discord.Embed]:
    """Create tag list embed pages for the redbot menu coroutine.
    For 500 max. chars per tag description, we list 3 entries per page.

    It features the following:
    - Each entry is numbered.
    - The total number of items is visible.
    - The total number of pages is visible.

    Parameters
    ----------
    descDict: Dict[ str, str ]
        A dict containing user IDs and descriptions.
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

    pageContents = []
    dictEntries = list(filter(lambda kv: kv[1], descDict.items()))

    # iterate through 3 entries at once in dict
    # then join them by line feed and add them to contents array
    STEP = 3
    for i in range(0, len(dictEntries), STEP):
        descList = []
        for userId, descText in dictEntries[i : i + STEP]:
            descList.append("\n".join([f"**<@{userId}>:**", box(descText)]))
        descText = "\n".join(descList)
        pageContents.append(descText)

    # convert contents array to embeds
    pageList = []
    totalPages = len(pageContents)
    totalEntries = len(dictEntries)

    async for pageNumber, page in AsyncIter(pageContents).enumerate(start=1):
        embed = discord.Embed(title=embedTitle, description=page)
        embed.set_footer(text=f"Page {pageNumber}/{totalPages} ({totalEntries} entries)")
        if embedAuthor:
            embed.set_author(
                name=embedAuthor.display_name,
                icon_url=embedAuthor.avatar_url or embedAuthor.default_avatar_url,
            )
        pageList.append(embed)

    return pageList
