import tracemoepy
from tracemoepy.errors import EmptyImage, EntityTooLarge, ServerError, TooManyRequests

async def postSourceFunction(self, ctx, imageURL):
    """helper method
    """
    try:
        tracemoe = tracemoepy.tracemoe.TraceMoe()
        result = tracemoe.search(imageURL.strip("<>"), is_url=True)
        titleEnglish = result.docs[0].title_english
        anilistID = f"{result.docs[0].anilist_id}"
        episode = f"{result.docs[0].episode}"
        similarity = float(result.docs[0].similarity)
        URL = "https://anilist.co/anime/" + anilistID

        # embed = Embed(title=titleEnglish, url=URL)
        # embed.add_field(name="Episode", value=episode)
        # embed.add_field(name="Similarity", value=('%.3f'%((similarity)*100)))
        if similarity < 0.8:
            await ctx.send(
                "Anime: "
                + titleEnglish
                + "\nEpisode: "
                + episode
                + "\nWARNING: Similarity less than 80%, result may not be accurate"
                + "\n"
                + URL
            )
        else:
            await ctx.send(
                "Anime: "
                + titleEnglish
                + "\nSimilarity: "
                + ("%.3f" % ((similarity) * 100))
                + "%"
                + "\nEpisode: "
                + episode
                + "\n"
                + URL
            )
        # await ctx.send(embed=embed)
    except TooManyRequests:
        await ctx.send("Please try again later")
    except EntityTooLarge:
        await ctx.send("Too big of file image")
    except ServerError:
        await ctx.send(
            "Server error. Ensure image is provided as URL and points directly to png or jpg image"
        )
    except EmptyImage:
        await ctx.send(
            "Empty image provided. Ensure image is provided as URL and points directly to png or jpg image"
        )
