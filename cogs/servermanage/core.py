import asyncio
from datetime import date, datetime, timedelta
import logging
from os import remove
from os.path import splitext, join as pathJoin
from pathlib import Path

import discord

from redbot.core import Config, data_manager
from redbot.core.commands.context import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import error, pagify, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.bot import Red

from .constants import *
from .exceptions import InvalidAttachmentsError, InvalidFileError, InvalidImageError


class Core:
    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        # Register default (empty) settings.
        self.config.register_guild(**BASE_GUILD)

        # Initialize logger, and save to cog folder.
        self.dataFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.ServerManage")
        if not self.logger.handlers:
            logPath = pathJoin(self.dataFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%Y/%m/%d %H:%M:%S]")
            )
            self.logger.addHandler(handler)

        # On cog load, we want the loop to run once.
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.imageLoop())

    # Cancel the background task on cog unload.
    def __unload(self):
        self.logger.info("Cancelling background task")
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()

    async def imageLoop(self):
        while self == self.bot.get_cog("ServerManage"):
            if self.lastChecked.day != datetime.now().day:
                self.logger.info("Checking to see if we need to change server images")
                self.lastChecked = datetime.now()
                for guild in self.bot.guilds:
                    await self.checkGuildIcons(guild)
                    await self.checkGuildBanners(guild)
            await asyncio.sleep(60)
        self.logger.error("We should never reach this!")

    async def checkGuildIcons(self, guild: discord.Guild):
        self.logger.debug("Checking guild icon for %s (%s)", guild.name, guild.id)
        today = datetime.now().strftime("%m-%d")
        iconDates = await self.config.guild(guild).get_attr(KEY_ICONS_DATES)()
        if today in iconDates:
            iconName = iconDates[today]
            icons = await self.config.guild(guild).get_attr(KEY_ICONS)()
            icon = icons[iconName]

            filepath = self.getFullFilepath(guild, icon)

            with open(filepath, "br") as icon:
                try:
                    await guild.edit(
                        icon=icon.read(), reason=f"ServerManage changing icon to {iconName}"
                    )
                    self.logger.info(
                        "Changed the server icon for %s (%s) to %s", guild.name, guild.id, iconName
                    )
                except discord.errors.Forbidden as error:
                    self.logger.error(
                        "Could not change icon, ensure the bot has Manage Server permissions",
                        exc_info=True,
                    )

    async def checkGuildBanners(self, guild: discord.Guild):
        self.logger.debug("Checking guild banner for %s (%s)", guild.name, guild.id)
        today = datetime.now().strftime("%m-%d")
        bannerDates = await self.config.guild(guild).get_attr(KEY_BANNERS_DATES)()
        if today in bannerDates:
            bannerName = bannerDates[today]
            banners = await self.config.guild(guild).get_attr(KEY_BANNERS)()
            banner = banners[bannerName]

            filepath = self.getFullFilepath(guild, banner, imageType="banners")

            with open(filepath, "br") as banner:
                try:
                    await guild.edit(
                        banner=banner.read(),
                        reason=f"ServerManage changing banner to {bannerName}",
                    )
                    self.logger.info(
                        "Changed the server banner for %s (%s) to %s",
                        guild.name,
                        guild.id,
                        bannerName,
                    )
                except discord.errors.Forbidden as error:
                    self.logger.error(
                        "Could not change banner, ensure the bot has Manage Server permissions",
                        exc_info=True,
                    )

    @staticmethod
    def validateImageAttachment(message: discord.Message):
        """Check to see if the message contains a valid image attachment.

        Parameters
        ----------
        message: discord.Message
            The message you wish to check.

        Raises
        ------
        InvalidFileError
            The attachment uploaded is not an image.
        InvalidImageError:
            The image uploaded is not a PNG or GIF.
        InvalidAttachmentsError:
            There isn't exactly one attachment.
        """
        attachments = message.attachments
        if len(attachments) != 1:
            raise InvalidAttachmentsError

        image = attachments[0]

        # Perform file validation: check width/height and file extension.
        if not image.height and not image.width:
            raise InvalidFileError

        if splitext(image.filename)[1].lower() not in [".png", ".gif"]:
            raise InvalidImageError

    @staticmethod
    def validDate(month: int, day: int):
        try:
            datetime(2020, month, day)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def getSingularImageType(imageType: str):
        if imageType == "icons":
            return "icon"
        elif imageType == "banners":
            return "banner"
        else:
            raise ValueError("Image type not defined!")

    def getFullFilepath(
        self, guild: discord.Guild, imageDetails: dict, imageType="icons", mkdir=False
    ):
        if imageType not in ["icons", "banners"]:
            raise ValueError("Image type not defined!")
        directory = pathJoin(self.dataFolder, str(guild.id), imageType)
        if mkdir:
            Path(directory).mkdir(parents=True, exist_ok=True)
        filename = imageDetails["filename"]
        filepath = pathJoin(directory, filename)
        return filepath

    async def imageAdd(self, ctx: Context, name: str, imageType="icons"):
        """Add an image to the database

        Parameters
        ----------
        ctx: Context
        name: str
            The name of the image to add.
        type: str
            One of either icons or banners
        """
        imageSingular = self.getSingularImageType(imageType)

        try:
            self.validateImageAttachment(ctx.message)
        except InvalidAttachmentsError:
            await ctx.send("Please attach one file!")
            return
        except InvalidFileError:
            await ctx.send("The file is not an image, please upload an image!")
            return
        except InvalidImageError:
            await ctx.send("Please upload a PNG or GIF image!")
            return
        images = await self.config.guild(ctx.guild).get_attr(imageType)()
        if name in images.keys():

            def check(msg: discord.Message):
                return msg.author == ctx.message.author and msg.channel == ctx.message.channel

            await ctx.send(
                warning(
                    f"This {imageSingular} already exists. Would you like to overwrite "
                    "it? Please type `yes` to overwrite."
                )
            )
            try:
                response = await self.bot.wait_for("message", timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send(f"You took too long, not overwriting the existing {imageSingular}.")
                return

            if response.content.lower() != "yes":
                await ctx.send(f"Not overwriting the {imageSingular}.")
                return

        # Save the image
        image = ctx.message.attachments[0]
        extension = splitext(image.filename)[1].lower()
        imageDict = {}
        imageDict["filename"] = f"{name}{extension}"
        filepath = self.getFullFilepath(ctx.guild, imageDict, imageType=imageType, mkdir=True)
        await ctx.message.attachments[0].save(filepath, use_cached=False)
        async with self.config.guild(ctx.guild).get_attr(imageType)() as images:
            images[name] = imageDict
        await ctx.send(f"Saved the {imageSingular} as {name}!")
        self.logger.info(
            "User %s#%s (%s) added a(n) %s '%s%s'",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            imageSingular,
            name,
            extension,
        )

    async def imageRemove(self, ctx: Context, name: str, imageType="icons"):
        """Remove an image from the database

        Parameters
        ----------
        ctx: Context
        name: str
            The name of the image to remove.
        type: str
            One of either icons or banners
        """
        imageSingular = self.getSingularImageType(imageType)

        # Check to see if this image exists in dictionary
        images = await self.config.guild(ctx.guild).get_attr(imageType)()
        if name not in images.keys():
            await ctx.send(f"This {imageSingular} doesn't exist!")
            return

        def check(msg: discord.Message):
            return msg.author == ctx.message.author and msg.channel == ctx.message.channel

        await ctx.send(warning(f"Are you sure you want to delete? Please type `yes` to confirm."))
        try:
            response = await self.bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send(f"You took too long, not deleting the {imageSingular}.")
            return

        if response.content.lower() != "yes":
            await ctx.send(f"Not deleting the {imageSingular}.")
            return

        # Delete image
        filepath = self.getFullFilepath(ctx.guild, images[name], imageType=imageType)
        filename = images[name]["filename"]
        try:
            remove(filepath)
        except FileNotFoundError:
            self.logger.error("File does not exist %s", filepath)

        # Delete key from dictionary
        async with self.config.guild(ctx.guild).get_attr(imageType)() as images:
            del images[name]
        async with self.config.guild(ctx.guild).get_attr(f"{imageType}Dates")() as dates:
            datesToRemove = []
            for date, imageName in dates.items():
                if name == imageName:
                    self.logger.debug(
                        "The date %s has this %s, deleting from dates dict", date, imageName
                    )
                    datesToRemove.append(date)
            for date in datesToRemove:
                del dates[date]

        await ctx.send(f"Deleted the {imageSingular} named {name}!")
        self.logger.info(
            "User %s#%s (%s) deleted a(n) %s '%s'",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            imageSingular,
            filename,
        )

    async def imageShow(self, ctx: Context, name: str, imageType="icons"):
        """Show an image from the database.

        Parameters
        ----------
        ctx: Context
        name: str
            The image name you wish to show.
        type: str
            One of either icons or banners.
        """
        imageSingular = self.getSingularImageType(imageType)

        # Check to see if this icon exists in dictionary
        images = await self.config.guild(ctx.guild).get_attr(imageType)()
        if name not in images.keys():
            await ctx.send(f"This {imageSingular} doesn't exist!")
            return

        filepath = self.getFullFilepath(ctx.guild, images[name], imageType=imageType)

        # Send file to discord
        try:
            image = discord.File(filepath, filename=images[name]["filename"])
            await ctx.send(file=image)
        except FileNotFoundError:
            await ctx.send(error("The file does not exist"))
            self.logger.error("File does not exist %s", filepath)

    async def imageList(self, ctx: Context, imageType="icons"):
        """For a given imageType, list the images associated with each date.

        Parameters
        ----------
        ctx: Context
        imageType: str
            One of either icons or banners
        """
        imageSingular = self.getSingularImageType(imageType)
        allImages = await self.config.guild(ctx.guild).get_attr(imageType)()
        if not allImages:
            await ctx.send(f"There are no {imageType}, please add some first!")
            return

        async with self.config.guild(ctx.guild).get_attr(f"{imageType}Dates")() as imageDates:
            imageDates = dict(sorted(imageDates.items()))
            msg = ""
            for changeDate, name in imageDates.items():
                # YYYY-MM-DD
                theDate = date.fromisoformat(f"2020-{changeDate}").strftime("%B %d")
                msg += f"{theDate}: {name}\n"
            notAssigned = set(allImages) - set(imageDates.values())
            if notAssigned:
                msg += f"Unassigned: "
                msg += ", ".join(notAssigned)
        pageList = []
        pages = list(pagify(msg, page_length=500))
        totalPages = len(pages)
        async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
            embed = discord.Embed(
                title=f"Server {imageSingular} changes for {ctx.guild.name}", description=page
            )
            embed.set_footer(text=f"Page {pageNumber}/{totalPages}")
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    async def imageDateSet(self, ctx: Context, month: int, day: int, name: str, imageType="icons"):
        """Set when to change the image.

        Parameters
        ----------
        ctx: Context
        month: int
            The month to change the image, expressed as a number.
        day: int
            The day of the month to change the image, expressed as a number.
        name: str
            The name of the image to change to. The image should already be added.
        imageType: str
            One of either icons or banners.
        """
        imageSingular = self.getSingularImageType(imageType)

        if not self.validDate(month, day):
            await ctx.send("Please enter a valid date!")
            return
        if name not in await self.config.guild(ctx.guild).get_attr(imageType)():
            await ctx.send(f"This {imageSingular} doesn't exist!")
            return

        async with self.config.guild(ctx.guild).get_attr(f"{imageType}Dates")() as imageDates:
            theDate = datetime(2020, month, day)
            storageDate = theDate.strftime("%m-%d")
            humanDate = theDate.strftime("%B %d")
            imageDates[storageDate] = name
            await ctx.send(f"On {humanDate}, the server {imageSingular} will change to {name}")

    async def imageDateReset(self, ctx: Context, month: int, day: int, imageType="icons"):
        """Remove a date when to change the image.

        Parameters
        ----------
        ctx: Context
        month: int
            The month to remove any server icon changes, expressed as a number.
        day: int
            The day of the month to remove any server icon changes, expressed as a number.
        imageType: str
            One of either icons or banners.
        """
        imageSingular = self.getSingularImageType(imageType)

        if not self.validDate(month, day):
            await ctx.send("Please enter a valid date!")
            return
        async with self.config.guild(ctx.guild).get_attr(f"{imageType}Dates")() as imageDates:
            theDate = datetime(2020, month, day)
            storageDate = theDate.strftime("%m-%d")
            humanDate = theDate.strftime("%B %d")
            if storageDate in imageDates:
                del imageDates[storageDate]
                await ctx.send(f"Removed {humanDate} from {imageSingular} changes.")
            else:
                await ctx.send(f"There are no {imageSingular} changes on this date!")
