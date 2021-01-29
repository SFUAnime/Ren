from redbot.core import commands
import tracemoepy
from tracemoepy.errors import EmptyImage, EntityTooLarge, ServerError, TooManyRequests
from .postSource import postSourceFunction


class Source(commands.Cog):
    # @commands.command()
    @commands.group(name="source", invoke_without_command=True)
    async def sourceCommand(self, ctx):
        """Looks for source of image

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
            await postSourceFunction(self, ctx, imageURL)
            return


    # @commands.command()
    @sourceCommand.command(name="url")
    async def urlSource(self, ctx, imageURL):
        """Looks for source of image

        Parameters:
        -----------
        imageURL: a url pointing to a image from an anime episode. Can be surrounded with <> to suppress embeds in Discord
        """
        await postSourceFunction(self, ctx, imageURL)
