from redbot.core import commands
import tracemoepy
from tracemoepy.errors import EmptyImage, EntityTooLarge, ServerError, TooManyRequests


def messageBuilder(titleEnglish: str, anilistID: str, episode: str, similarity: int):
    """Builds the message that is sent in response"""
    # If the title isn't found, just return no matching anime found
    if titleEnglish == "No Title Found":
        return "No matching anime found.\nThis could be because provided picture isn't a screenshot of an anime, or the episode it's from is too new"
    # Title of anime
    message = f"Anime: {titleEnglish}"
    # episode number
    message += f"\nEpisode: {episode}"
    # How similar message is
    message += f"\nSimilarity: {similarity*100:.3f}%"
    if similarity * 100 < 90:
        # warning if similarity is less than 90%
        message += "\nWARNING: Similarity less than 90%, result may not be accurate"
    if anilistID != "No anilistID Found":
        # URL
        message += f"\nhttps://anilist.co/anime/{anilistID}"
    return message


async def postSourceFunction(ctx, imageURL):
    """helper method"""
    try:
        # use the API to get results
        tracemoe = tracemoepy.tracemoe.TraceMoe()
        result = tracemoe.search(imageURL.strip("<>"), is_url=True)
        titleEnglish = result.docs[0].title_english or "No Title Found"
        anilistID = f"{result.docs[0].anilist_id}" or "No anilistID Found"
        episode = f"{result.docs[0].episode}" or "No Episode Found"
        similarity = float(result.docs[0].similarity) or 0

        # send the message using messageBGuilder to build the message
        await ctx.send(messageBuilder(titleEnglish, anilistID, episode, similarity))

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


class Source(commands.Cog):
    @commands.group(name="source", invoke_without_command=True)
    async def sourceCommand(self, ctx):
        """Looks for source of a screenshot from anime, using trace.moe

        Parameters:
        -----------
        make sure to attach a png or jpg image, or type 'source url URL_HERE'
        """
        await ctx.trigger_typing()
        if not ctx.message.attachments:
            await ctx.send_help(command="source")
            return
        else:
            imageURL = ctx.message.attachments[0].url
            await postSourceFunction(ctx, imageURL)
            return

    @sourceCommand.command(name="url")
    async def urlSource(self, ctx, imageURL):
        """Looks for source of a screenshot from anime, using trace.moe

        Parameters:
        -----------
        imageURL: a url pointing to a image from an anime episode. Can be surrounded with <> to suppress embeds in Discord
        """
        await postSourceFunction(ctx, imageURL)
