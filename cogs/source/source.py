from redbot.core import commands
import tracemoepy
from tracemoepy.errors import TooManyRequests
from tracemoepy.errors import EntityTooLarge
from tracemoepy.errors import ServerError
from tracemoepy.errors import EmptyImage
import math
from discord import Embed


class Source(commands.Cog):
    """Looks up source of anime and pictures, may get NSFW results. Requires tracemoepy to be installed"""

    """ run 'pip install tracemoepy' on your redbot virtual environment to install"""

    # @commands.command()
    @commands.group(name="source")
    async def sourceCommand(self, ctx):
        """
        Looks for source of image

        Parameters:
        -----------
        make sure to attach a png or jpg image, or type 'source url URL_HERE'
        """

        helpmsg = "Looks for source of image\nMake sure to attach a png or jpg image, or type 'source url URL_HERE'"
        tracemoe = tracemoepy.tracemoe.TraceMoe()
        try:
            await ctx.trigger_typing()
            try:
                attachment = ctx.message.attachments[0].url
            except:
                return
            result = tracemoe.search(attachment.strip("<>"), is_url=True)
            titleEnglish = f"{result.docs[0].title_english}"
            anilistID = f"{result.docs[0].anilist_id}"
            episode = f"{result.docs[0].episode}"
            similarity = float(f"{result.docs[0].similarity}")
            URL = "https://anilist.co/anime/" + anilistID

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
        except TooManyRequests:
            await ctx.send("Too many requests sent")
        except EntityTooLarge:
            await ctx.send("Too big of file image")
        except ServerError:
            await ctx.send(
                "Server error. Ensure image is provided as URL and points directly to png or jpg image"
            )
        # except InvalidToken:
        #    await ctx.send("Invalid token")
        except EmptyImage:
            await ctx.send(
                "Empty image provided. Ensure image is provided as URL and points directly to png or jpg image"
            )
        # except InvalidPath:
        #    await ctx.send("Invalid path, bot had an error with .save method")

    # @commands.command()
    @sourceCommand.command(name="url")
    async def urlSource(self, ctx, imageURL):
        """
        Looks for source of image

        Parameters:
        -----------
        imageURL: a url pointing to a image from an anime episode. Can be surrounded with < or > to supressed embeds in discord
        """
        tracemoe = tracemoepy.tracemoe.TraceMoe()
        try:
            await ctx.trigger_typing()
            result = tracemoe.search(imageURL.strip("<>"), is_url=True)
            titleEnglish = f"{result.docs[0].title_english}"
            anilistID = f"{result.docs[0].anilist_id}"
            episode = f"{result.docs[0].episode}"
            similarity = float(f"{result.docs[0].similarity}")
            URL = "https://anilist.co/anime/" + anilistID

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
        except TooManyRequests:
            await ctx.send("Too many requests sent")
        except EntityTooLarge:
            await ctx.send("Too big of file image")
        except ServerError:
            await ctx.send(
                "Server error. Ensure image is provided as URL and points directly to png or jpg image"
            )
        # except InvalidToken:
        #    await ctx.send("Invalid token")
        except EmptyImage:
            await ctx.send(
                "Empty image provided. Ensure image is provided as URL and points directly to png or jpg image"
            )
        # except InvalidPath:
        #    await ctx.send("Invalid path, bot had an error with .save method")
