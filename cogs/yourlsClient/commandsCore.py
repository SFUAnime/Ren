import asyncio
from datetime import timezone
from functools import partial

import discord
from requests.exceptions import HTTPError, RequestException
import yourls

from redbot.core.commands.context import Context
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .constants import DEFAULT_ERROR, KEY_API, KEY_SIGNATURE
from .core import Core
from .exceptions import YOURLSNotConfigured
from .helpers import createSimplePages


class CommandsCore(Core):
    async def cmdStats(self, ctx: Context):
        """Get instance-wide statistics."""
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            urls, stats = await self.loop.run_in_executor(
                None, partial(shortener.stats, "top", limit=3)
            )
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

    async def cmdAdd(self, ctx: Context, keyword: str, longUrl: str):
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
            url = await self.loop.run_in_executor(
                None, partial(shortener.shorten, longUrl, keyword=keyword)
            )
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

    async def cmdDelete(self, ctx: Context, keyword: str):
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
            await self.loop.run_in_executor(None, shortener.delete, keyword)
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

    async def cmdRename(self, ctx: Context, oldKeyword: str, newKeyword: str):
        """Rename a keyword.

        Parameters
        ----------
        oldKeyword: str
            The original keyword.
        newKeyword: str
            The new keyword.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            await self.loop.run_in_executor(None, shortener.rename, oldKeyword, newKeyword)
        except YOURLSNotConfigured as error:
            await ctx.send(error)
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
            elif error.response.status_code == 409:
                self.logger.debug(
                    "%s (%s) attempted to rename %s for %s (%s), but the keyword %s was "
                    "already in use.",
                    ctx.author.name,
                    ctx.author.id,
                    oldKeyword,
                    ctx.guild.name,
                    ctx.guild.id,
                    newKeyword,
                    exc_info=True,
                )
                await ctx.send(
                    f"Keyword {newKeyword} is already used, please choose another keyword!"
                )
            elif error.response.status_code == 404:
                await ctx.send(
                    "Could not find the keyword, please make sure it is correct and try again!"
                )
            else:
                await ctx.send(DEFAULT_ERROR)
        else:
            self.logger.info(
                "%s (%s) renamed short URL %s to %s in %s (%s)",
                ctx.author.name,
                ctx.author.id,
                oldKeyword,
                newKeyword,
                ctx.guild.name,
                ctx.guild.id,
            )
            await ctx.send(f"Short URL renamed to {newKeyword}")

    async def cmdEdit(self, ctx: Context, keyword: str, newLongUrl: str):
        """Edit the long URL for a given keyword.

        Parameters
        ----------
        keyword: str
            The keyword to edit.
        newLongUrl: str
            The new URL that this keyword should point to.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            await self.loop.run_in_executor(None, shortener.edit, keyword, newLongUrl)
        except YOURLSNotConfigured as error:
            await ctx.send(error)
        except HTTPError as error:
            self.logger.error(
                "%s (%s) attempted to edit %s for %s (%s), but something went "
                "wrong. Please see the traceback for more info",
                ctx.author.name,
                ctx.author.id,
                keyword,
                ctx.guild.name,
                ctx.guild.id,
                exc_info=True,
            )
            if error.response.status_code == 429:
                await ctx.send("You're creating URLs too fast, please try again shortly.")
            elif error.response.status_code == 404:
                await ctx.send(
                    "Could not find the keyword, please make sure it is correct and try again!"
                )
            else:
                await ctx.send(DEFAULT_ERROR)
        else:
            self.logger.info(
                "%s (%s) changed short URL %s to point to %s in %s (%s)",
                ctx.author.name,
                ctx.author.id,
                keyword,
                newLongUrl,
                ctx.guild.name,
                ctx.guild.id,
            )
            await ctx.send(f"Short URL {keyword} now points to {newLongUrl}")

    async def cmdSearch(self, ctx: Context, searchTerm: str):
        """Get a list of keywords that resemble `searchTerm`.

        Parameters
        ----------
        searchTerm: str
            The search term to look for in YOURLS.
            e.g. The keyword of `https://example.com/discord` is `discord`.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            results = await self.loop.run_in_executor(None, shortener.search, searchTerm)
        except RuntimeError as error:
            await ctx.send(error)
        except HTTPError as error:
            if error.response.status_code == 404:
                await ctx.send(
                    "Did not find any matches, please try again with different parameters!"
                )
            else:
                self.logger.error(error, exc_info=True)
                await ctx.send(DEFAULT_ERROR)
        except RequestException as error:
            self.logger.error(error)
            await ctx.send(DEFAULT_ERROR)
        else:
            pageList = await createSimplePages(results, "Found the following keywords:")
            await menu(ctx, pageList, DEFAULT_CONTROLS)

    async def cmdUrlInfo(self, ctx: Context, keyword: str):
        """Get keyword-specific information.

        Parameters
        ----------
        keyword: str
            The keyword used for the shortened URL.
            e.g. The keyword of `https://example.com/discord` is `discord`.
        """
        try:
            shortener = await self.fetchYourlsClient(ctx.guild)
            urlStats = await self.loop.run_in_executor(None, shortener.url_stats, keyword)
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
            if error.response.status_code == 404:
                await ctx.send(
                    "Could not find the keyword, please make sure it is correct and try again!"
                )
            else:
                self.logger.error(error, exc_info=True)
                await ctx.send(DEFAULT_ERROR)
        except RequestException as error:
            self.logger.error(error)
            await ctx.send(DEFAULT_ERROR)
        else:
            await ctx.send(embed=embed)

    async def cmdApi(self, ctx: Context, apiEndpoint: str):
        """Configure the API endpoint for YOURLS.

        Parameters
        ----------
        apiEndpoint: str
            The URL to the YOURLS API endpoint.
        """
        await self.config.guild(ctx.guild).get_attr(KEY_API).set(apiEndpoint)
        self.logger.info(
            "%s (%s) modified the YOURLS API endpoint for %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.guild.name,
            ctx.guild.id,
        )
        await ctx.send(f"API endpoint set to {apiEndpoint}")

    async def cmdSig(self, ctx: Context, signature: str):
        """Configure the API signature for YOURLS.

        Parameters
        ----------
        signature: str
            The signature to access the YOURLS API endpoint.
        """
        await self.config.guild(ctx.guild).get_attr(KEY_SIGNATURE).set(signature)
        self.logger.info(
            "%s (%s) modified the YOURLS signature for %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.guild.name,
            ctx.guild.id,
        )
        await ctx.send(f"API signature set.")
        await ctx.message.delete()
