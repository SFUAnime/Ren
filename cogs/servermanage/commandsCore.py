from redbot.core.commands.context import Context

from .constants import IMAGE_BANNERS
from .core import Core


class CommandsCore(Core):
    async def cmdIconAdd(self, ctx: Context, iconName: str):
        """Add a server icon to the database.

        Parameters
        ----------
        iconName: str
            The name of the icon you wish to add.
        image: attachment
            The server icon, included as an attachment.
        """
        return await self.imageAdd(ctx=ctx, name=iconName, imageType="icons")

    async def cmdIconRemove(self, ctx: Context, iconName: str):
        """Remove a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to remove.
        """
        return await self.imageRemove(ctx=ctx, name=iconName)

    async def cmdIconShow(self, ctx: Context, iconName: str):
        """Show a server icon from the database.

        Parameters
        ----------
        iconName: str
            The icon name you wish to show.
        """
        await self.imageShow(ctx=ctx, name=iconName)

    async def cmdIconList(self, ctx: Context):
        """List the server icons associated with each date."""
        return await self.imageList(ctx)

    async def cmdIconSet(self, ctx: Context, month: int, day: int, iconName: str):
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
        await self.imageDateSet(ctx=ctx, month=month, day=day, name=iconName)

    async def cmdIconReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server icon.

        Parameters
        ----------
        month: int
            The month to remove any server icon changes, expressed as a number.
        day: int
            The day of the month to remove any server icon changes, expressed as a number.
        """
        await self.imageDateReset(ctx=ctx, month=month, day=day)

    async def cmdBannerAdd(self, ctx: Context, bannerName: str):
        """Add a server banner to the database.

        Parameters
        ----------
        bannerName: str
            The name of the banner you wish to add.
        image: attachment
            The server banner, included as an attachment.
        """
        return await self.imageAdd(ctx=ctx, name=bannerName, imageType=IMAGE_BANNERS)

    async def cmdBannerRemove(self, ctx: Context, bannerName: str):
        """Remove a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to remove.
        """
        return await self.imageRemove(ctx=ctx, name=bannerName, imageType=IMAGE_BANNERS)

    async def cmdBannerShow(self, ctx: Context, bannerName: str):
        """Show a server banner from the database.

        Parameters
        ----------
        bannerName: str
            The banner name you wish to show.
        """
        await self.imageShow(ctx=ctx, name=bannerName, imageType=IMAGE_BANNERS)

    async def cmdBannerList(self, ctx: Context):
        """List the server banners associated with each date."""
        return await self.imageList(ctx=ctx, imageType=IMAGE_BANNERS)

    async def cmdBannerSet(self, ctx: Context, month: int, day: int, bannerName: str):
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
        await self.imageDateSet(
            ctx=ctx, month=month, day=day, name=bannerName, imageType=IMAGE_BANNERS
        )

    async def cmdBannerReset(self, ctx: Context, month: int, day: int):
        """Remove a date when to change the server banner.

        Parameters
        ----------
        month: int
            The month to remove any server banner changes, expressed as a number.
        day: int
            The day of the month to remove any server banner changes, expressed as a number.
        """
        await self.imageDateReset(ctx=ctx, month=month, day=day, imageType=IMAGE_BANNERS)
