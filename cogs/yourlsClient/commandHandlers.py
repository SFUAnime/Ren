from redbot.core import checks, commands
from redbot.core.commands.context import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="yourls")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def _grpYourlsBase(self, ctx: Context):
        """Manage the YOURLS instance"""

    @_grpYourlsBase.command(name="stats")
    async def _cmdStats(self, ctx: Context):
        """Get instance-wide statistics."""
        await self.cmdStats(ctx=ctx)

    @_grpYourlsBase.command(name="add", aliases=["shorten"])
    async def _cmdAdd(self, ctx: Context, keyword: str, longUrl: str):
        """Create a new, shortened URL.

        Parameters
        ----------
        keyword: str
            The keyword you want to use to refer to the long URL.
        longUrl: str
            The long URL you wish to shorten.
        """
        await self.cmdAdd(ctx=ctx, keyword=keyword, longUrl=longUrl)

    @_grpYourlsBase.command(name="del", aliases=["delete", "remove", "rm"])
    async def _cmdDelete(self, ctx: Context, keyword: str):
        """Delete a shortened URL.

        Parameters
        ----------
        keyword: str
            The keyword used to refer to the long URL.
        """
        await self.cmdDelete(ctx=ctx, keyword=keyword)

    @_grpYourlsBase.command(name="rename")
    async def _cmdRename(self, ctx: Context, oldKeyword: str, newKeyword: str):
        """Rename a keyword.

        Parameters
        ----------
        oldKeyword: str
            The original keyword.
        newKeyword: str
            The new keyword.
        """
        await self.cmdRename(ctx=ctx, oldKeyword=oldKeyword, newKeyword=newKeyword)

    @_grpYourlsBase.command(name="edit")
    async def _cmdEdit(self, ctx: Context, keyword: str, newLongUrl: str):
        """Edit the long URL for a given keyword.

        Parameters
        ----------
        keyword: str
            The keyword to edit.
        newLongUrl: str
            The new URL that this keyword should point to.
        """
        await self.cmdEdit(ctx=ctx, keyword=keyword, newLongUrl=newLongUrl)

    @_grpYourlsBase.command(name="search")
    async def _cmdSearch(self, ctx: Context, searchTerm: str):
        """Get a list of keywords that resemble `searchTerm`.

        Parameters
        ----------
        searchTerm: str
            The search term to look for in YOURLS.
            e.g. The keyword of `https://example.com/discord` is `discord`.
        """
        await self.cmdSearch(ctx=ctx, searchTerm=searchTerm)

    @_grpYourlsBase.command(name="info")
    async def _cmdUrlInfo(self, ctx: Context, keyword: str):
        """Get keyword-specific information.

        Parameters
        ----------
        keyword: str
            The keyword used for the shortened URL.
            e.g. The keyword of `https://example.com/discord` is `discord`.
        """
        await self.cmdUrlInfo(ctx=ctx, keyword=keyword)

    @_grpYourlsBase.group(name="settings")
    async def _grpSettingsBase(self, ctx: Context):
        """Configure the YOURLS connection"""

    @_grpSettingsBase.command(name="api")
    async def _cmdApi(self, ctx: Context, apiEndpoint: str):
        """Configure the API endpoint for YOURLS.

        Parameters
        ----------
        apiEndpoint: str
            The URL to the YOURLS API endpoint.
        """
        await self.cmdApi(ctx=ctx, apiEndpoint=apiEndpoint)

    @_grpSettingsBase.command(name="signature", aliases=["sig"])
    async def _cmdSig(self, ctx: Context, signature: str):
        """Configure the API signature for YOURLS.

        Parameters
        ----------
        signature: str
            The signature to access the YOURLS API endpoint.
        """
        await self.cmdSig(ctx=ctx, signature=signature)
