"""YOURLS module

Control Your Own URL Shortener instance.
"""
import asyncio
from datetime import timezone
import logging
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

from requests.exceptions import HTTPError, RequestException
import yourls
from yourls import YOURLSClientBase, YOURLSAPIMixin

from .exceptions import *


BASE_GUILD = {
    "api": None,
    "signature": None,
}
DEFAULT_ERROR = "Something went wrong, please try again later, or check your console for details."


class YOURLSDeleteMixin(object):
    def delete(self, short):
        data = dict(action="delete", shorturl=short)
        self._api_request(params=data)


class YOURLSClient(YOURLSDeleteMixin, YOURLSAPIMixin, YOURLSClientBase):
    """YOURLS client with API delete support."""


class YOURLS(commands.Cog):
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)

        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.YOURLS")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename=str(saveFolder) + "/info.log", encoding="utf-8", mode="a"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    @commands.group(name="yourls")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def yourlsBase(self, ctx: Context):
        """Manage the YOURLS instance"""

    @yourlsBase.command(name="stats")
    async def stats(self, ctx: Context):
        """Get instance-wide statistics."""
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            urls, stats = shortener.stats("top", limit=3)
            embed = discord.Embed()
            emoji = 129351  # first_place
            for url in urls:
                actualEmoji = chr(emoji)
                print(url)
                value = f"**URL**: {url.shorturl}\n"
                value += f"**Clicks**: {url.clicks}"
                embed.add_field(name=f"{actualEmoji} URL", value=value, inline=False)
                emoji += 1
        except RuntimeError as error:
            await ctx.send(error)
        except HTTPError as error:
            self.logger.error(error, exc_info=True)
            await ctx.send(DEFAULT_ERROR)
        except RequestException as error:
            self.logger.error(error, exc_info=True)
            await ctx.send(DEFAULT_ERROR)
        else:
            await ctx.send(
                content=f"Tracking **{stats.total_links}** links, **{stats.total_clicks}** "
                "clicks, and counting!",
                embed=embed,
            )

    @yourlsBase.command(name="add", aliases=["shorten"])
    async def add(self, ctx: Context, keyword: str, longUrl: str):
        """Create a new, shortened URL.

        Parameters
        ----------
        keyword: str
            The keyword you want to use to refer to the long URL.
        longUrl: str
            The long URL you wish to shorten.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            url = shortener.shorten(longUrl, keyword=keyword)
            self.logger.info(
                "%s (%s) added a short URL at %s for %s (%s)",
                ctx.author.name,
                ctx.author.id,
                url.shorturl,
                ctx.guild.name,
                ctx.guild.id,
            )
        except YOURLSNotConfigured as error:
            await ctx.send(error)
        except yourls.exceptions.YOURLSKeywordExistsError as error:
            self.logger.debug(
                "%s (%s) attempted to add a short URL for %s (%s), but the keyword %s was "
                "already in use.",
                ctx.author.name,
                ctx.author.id,
                keyword,
                ctx.guild.name,
                ctx.guild.id,
                exc_info=True,
            )
            await ctx.send(
                f"Keyword {error.keyword} is already used, please choose another keyword!"
            )
        except yourls.exceptions.YOURLSURLExistsError as error:
            await ctx.send(f"The long URL was already shortened before, see {error.url.shorturl}")
        except HTTPError as error:
            self.logger.error(
                "%s (%s) attempted to add a short URL for %s (%s), but something went "
                "wrong. Please see the traceback for more info",
                ctx.author.name,
                ctx.author.id,
                ctx.guild.name,
                ctx.guild.id,
                exc_info=True,
            )
            if error.response.status_code == 429:
                await ctx.send("You're creating URLs too fast, please try again shortly.")
            else:
                await ctx.send(DEFAULT_ERROR)
        else:
            await ctx.send(f"Short URL created: <{url.shorturl}>")

    @yourlsBase.command(name="del", aliases=["delete", "remove", "rm"])
    async def delete(self, ctx: Context, keyword: str):
        """Delete a shortened URL.

        Parameters
        ----------
        keyword: str
            The keyword used to refer to the long URL.
        """

        def check(msg: discord.Message):
            return msg.author == ctx.message.author and msg.channel == ctx.message.channel

        await ctx.send(f"Are you sure you want to delete? Please type `yes` to confirm.")
        try:
            response = await self.bot.wait_for("message", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long, not deleting the short URL.")
            return

        if response.content.lower() != "yes":
            await ctx.send("Not deleting the short URL.")
            return

        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            url = shortener.delete(keyword)
            self.logger.info(
                "%s (%s) deleted the short URL %s for %s (%s)",
                ctx.author.name,
                ctx.author.id,
                keyword,
                ctx.guild.name,
                ctx.guild.id,
            )
        except YOURLSNotConfigured as error:
            await ctx.send(error)
        except HTTPError as error:
            self.logger.error(
                "%s (%s) attempted to delete the short URL %s for %s (%s), but something went "
                "wrong. Please see the traceback for more info",
                ctx.author.name,
                ctx.author.id,
                keyword,
                ctx.guild.name,
                ctx.guild.id,
                exc_info=True,
            )
            if error.response.status_code == 429:
                await ctx.send("You're deleting URLs too fast, please try again shortly.")
            elif error.response.status_code == 404:
                await ctx.send(f"{keyword} was not a shortened URL.")
            else:
                await ctx.send(DEFAULT_ERROR)
        else:
            await ctx.send(f"Short URL deleted.")

    @yourlsBase.command(name="info")
    async def urlInfo(self, ctx: Context, keyword: str):
        """Get keyword-specific information.

        Parameters
        ----------
        keyword: str
            The keyword used for the shortened URL.
            e.g. The keyword of `https://example.com/discord` is `discord`.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            urlStats = shortener.url_stats(keyword)
            urlDate = urlStats.date.replace(tzinfo=timezone.utc).astimezone(tz=None)
            urlDate = urlDate.strftime("%a, %d %b %Y %I:%M%p %Z")
            embed = discord.Embed()
            embed.title = f"URL stats for {keyword}"
            embed.add_field(name="Short URL", value=f"{urlStats.shorturl}", inline=False)
            if len(urlStats.url) > 1024:
                embed.add_field(name="Long URL", value=f"Too long to be displayed.", inline=False)
            else:
                embed.add_field(name="Long URL", value=f"{urlStats.url}", inline=False)
            embed.add_field(name="Date Created", value=f"{urlDate}", inline=False)
            embed.add_field(name="Clicks", value=f"{urlStats.clicks}", inline=False)
            embed.add_field(
                name="More Info (Login Required)",
                value=f"[Detailed Statistics]({urlStats.shorturl}+)",
                inline=False,
            )
        except RuntimeError as error:
            await ctx.send(error)
        except HTTPError as error:
            self.logger.error(error, exc_info=True)
            await ctx.send(DEFAULT_ERROR)
        except RequestException as error:
            self.logger.error(error)
            await ctx.send(DEFAULT_ERROR)
        else:
            await ctx.send(embed=embed)

    @yourlsBase.group(name="settings")
    async def settingsBase(self, ctx: Context):
        """Configure the YOURLS connection"""

    @settingsBase.command(name="api")
    async def api(self, ctx: Context, apiEndpoint: str):
        """Configure the API endpoint for YOURLS.

        Parameters
        ----------
        apiEndpoint: str
            The URL to the YOURLS API endpoint.
        """
        await self.config.guild(ctx.guild).api.set(apiEndpoint)
        self.logger.info(
            "%s (%s) modified the YOURLS API endpoint for %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.guild.name,
            ctx.guild.id,
        )
        await ctx.send(f"API endpoint set to {apiEndpoint}")

    @settingsBase.command(name="signature", aliases=["sig"])
    async def sig(self, ctx: Context, signature: str):
        """Configure the API endpoint for YOURLS.

        Parameters
        ----------
        signature: str
            The signature to access the YOURLS API endpoint.
        """
        await self.config.guild(ctx.guild).signature.set(signature)
        self.logger.info(
            "%s (%s) modified the YOURLS signature for %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.guild.name,
            ctx.guild.id,
        )
        await ctx.send(f"API signature set.")
        await ctx.message.delete()

    async def fetchYourlsClient(self, guild: discord.Guild):
        """Create the YOURLS client.

        Parameters
        ----------
        guild: discord.Guild
            The guild to look up the YOURLS API configuration for.

        Returns
        -------
        yourls.YOURLSClient
            The YOURLS client, which you can use to interact with your YOURLS instance.

        Raises
        ------
        YOURLSNotConfigured
            Unable to create the YOURLS client because of missing information.
        """
        api = await self.config.guild(guild).api()
        sig = await self.config.guild(guild).signature()
        if not (api and sig):
            raise YOURLSNotConfigured("Please configure the YOURLS API first.")
        return YOURLSClient(api, signature=sig)
