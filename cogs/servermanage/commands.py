from abc import ABC
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands.context import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import error, pagify, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.bot import Red

from .constants import IMAGE_BANNERS
from .meta import ServerManageMeta


class ServerManageCommands(ABC, metaclass=ServerManageMeta):
    @commands.group(name="servermanage")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def serverManage(self, ctx: Context):
        """Manage server icons and banners."""

    @serverManage.group(name="icons", aliases=["icon"])
    async def serverIcons(self, ctx: Context):
        """Manage server icons."""

    @serverIcons.command(name="add", aliases=["create"])
    async def iconAdd(self, ctx: Context, iconName: str):
        """Add a server icon to the database.

        Parameters
        ----------
        iconName: str
            The name of the icon you wish to add.
        image: attachment
            The server icon, included as an attachment.
        """
        return await self.imageAdd(ctx, iconName, imageType="icons")

    @serverIcons.command(name="remove", aliases=["del", "delete", "rm"])
    async def iconRemove(self, ctx: Context, iconName: str):
        """Remove a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to remove.
        """
        return await self.imageRemove(ctx, iconName)

    @serverIcons.command(name="show")
    async def iconShow(self, ctx: Context, iconName: str):
        """Show a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to show.
        """
        await self.imageShow(ctx, iconName)

    @serverIcons.command(name="list", aliases=["ls"])
    async def iconList(self, ctx: Context):
        """List the server icons associated with each date."""
        return await self.imageList(ctx)

    @serverIcons.command(name="set")
    async def iconSet(self, ctx: Context, month: int, day: int, iconName: str):
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
        await self.imageDateSet(ctx, month, day, iconName)

    @serverIcons.command(name="reset")
    async def iconReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server icon.

        Parameters
        ----------
        month: int
            The month to remove any server icon changes, expressed as a number.
        day: int
            The day of the month to remove any server icon changes, expressed as a number.
        """
        await self.imageDateReset(ctx, month, day)

    @serverManage.group(name="banners", aliases=["banner"])
    async def serverBanners(self, ctx: Context):
        """Manage server banners."""

    @serverBanners.command(name="add", aliases=["create"])
    async def bannerAdd(self, ctx: Context, bannerName: str):
        """Add a server banner to the database.

        Parameters
        ----------
        bannerName: str
            The name of the banner you wish to add.
        image: attachment
            The server banner, included as an attachment.
        """
        return await self.imageAdd(ctx, bannerName, imageType=IMAGE_BANNERS)

    @serverBanners.command(name="remove", aliases=["del", "delete", "rm"])
    async def bannerRemove(self, ctx: Context, bannerName: str):
        """Remove a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to remove.
        """
        return await self.imageRemove(ctx, bannerName, imageType=IMAGE_BANNERS)

    @serverBanners.command(name="show")
    async def bannerShow(self, ctx: Context, bannerName: str):
        """Show a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to show.
        """
        await self.imageShow(ctx, bannerName, imageType=IMAGE_BANNERS)

    @serverBanners.command(name="list", aliases=["ls"])
    async def bannerList(self, ctx: Context):
        """List the server banners associated with each date."""
        return await self.imageList(ctx, imageType=IMAGE_BANNERS)

    @serverBanners.command(name="set")
    async def bannerSet(self, ctx: Context, month: int, day: int, bannerName: str):
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
        await self.imageDateSet(ctx, month, day, bannerName, imageType=IMAGE_BANNERS)

    @serverBanners.command(name="reset")
    async def bannerReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server banner.

        Parameters
        ----------
        month: int
            The month to remove any server banner changes, expressed as a number.
        day: int
            The day of the month to remove any server banner changes, expressed as a number.
        """
        await self.imageDateReset(ctx, month, day, imageType=IMAGE_BANNERS)
