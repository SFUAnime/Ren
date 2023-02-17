from redbot.core import checks, commands
from redbot.core.commands.context import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="servermanage")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def _grpServerManage(self, ctx: Context):
        """Manage server icons and banners."""

    @_grpServerManage.group(name="icons", aliases=["icon"])
    async def _grpServerIcons(self, ctx: Context):
        """Manage server icons."""

    @_grpServerIcons.command(name="add", aliases=["create"])
    async def _cmdIconAdd(self, ctx: Context, iconName: str):
        """Add a server icon to the database.

        Parameters
        ----------
        iconName: str
            The name of the icon you wish to add.
        image: attachment
            The server icon, included as an attachment.
        """
        return await self.cmdIconAdd(ctx=ctx, iconName=iconName)

    @_grpServerIcons.command(name="remove", aliases=["del", "delete", "rm"])
    async def _cmdIconRemove(self, ctx: Context, iconName: str):
        """Remove a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to remove.
        """
        return await self.cmdIconRemove(ctx=ctx, iconName=iconName)

    @_grpServerIcons.command(name="show")
    async def _cmdIconShow(self, ctx: Context, iconName: str):
        """Show a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to show.
        """
        await self.cmdIconShow(ctx=ctx, iconName=iconName)

    @_grpServerIcons.command(name="list", aliases=["ls"])
    async def _cmdIconList(self, ctx: Context):
        """List the server icons associated with each date."""
        return await self.cmdIconList(ctx=ctx)

    @_grpServerIcons.command(name="set")
    async def _cmdIconSet(self, ctx: Context, month: int, day: int, iconName: str):
        """Set when to change the server icon.

        Parameters
        ----------
        month: int
            The month to change the server icon, expressed as a number.
        day: int
            The day of the month to change the server icon, expressed as a number.
        iconName: str
            The name of the server icon to change to. The icon should already be added.
        """
        await self.cmdIconSet(ctx=ctx, month=month, day=day, iconName=iconName)

    @_grpServerIcons.command(name="reset")
    async def _cmdIconReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server icon.

        Parameters
        ----------
        month: int
            The month to remove any server icon changes, expressed as a number.
        day: int
            The day of the month to remove any server icon changes, expressed as a number.
        """
        await self.cmdIconReset(ctx=ctx, month=month, day=day)

    @_grpServerManage.group(name="banners", aliases=["banner"])
    async def _grpServerBanners(self, ctx: Context):
        """Manage server banners."""

    @_grpServerBanners.command(name="add", aliases=["create"])
    async def _cmdBannerAdd(self, ctx: Context, bannerName: str):
        """Add a server banner to the database.

        Parameters
        ----------
        bannerName: str
            The name of the banner you wish to add.
        image: attachment
            The server banner, included as an attachment.
        """
        return await self.cmdBannerAdd(ctx=ctx, bannerName=bannerName)

    @_grpServerBanners.command(name="remove", aliases=["del", "delete", "rm"])
    async def _cmdBannerRemove(self, ctx: Context, bannerName: str):
        """Remove a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to remove.
        """
        return await self.cmdBannerRemove(ctx=ctx, bannerName=bannerName)

    @_grpServerBanners.command(name="show")
    async def _cmdBannerShow(self, ctx: Context, bannerName: str):
        """Show a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to show.
        """
        await self.cmdBannerShow(ctx=ctx, bannerName=bannerName)

    @_grpServerBanners.command(name="list", aliases=["ls"])
    async def _cmdBannerList(self, ctx: Context):
        """List the server banners associated with each date."""
        return await self.cmdBannerList(ctx=ctx)

    @_grpServerBanners.command(name="set")
    async def _cmdBannerSet(self, ctx: Context, month: int, day: int, bannerName: str):
        """Set when to change the server banner.

        Parameters
        ----------
        month: int
            The month to change the server banner, expressed as a number.
        day: int
            The day of the month to change the server banner, expressed as a number.
        bannerName: str
            The name of the server banner to change to. The banner should already be added.
        """
        await self.cmdBannerSet(ctx=ctx, month=month, day=day, bannerName=bannerName)

    @_grpServerBanners.command(name="reset")
    async def _cmdBannerReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server banner.

        Parameters
        ----------
        month: int
            The month to remove any server banner changes, expressed as a number.
        day: int
            The day of the month to remove any server banner changes, expressed as a number.
        """
        await self.cmdBannerReset(ctx=ctx, month=month, day=day)
