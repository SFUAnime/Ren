"""Catgirl cog.  Send random cute catgirls to a channel."""
import asyncio
import random
import discord
import requests
from redbot.core import checks, Config, commands
from redbot.core.bot import Red

# Global variables
KEY_CATGIRL = "catgirls"  # Key for JSON files.
KEY_CATBOY = "catboys"  # Key containing other images.
KEY_IMAGE_URL = "url"  # Key for URL
KEY_ISPIXIV = "is_pixiv"  # Key that specifies if image is from pixiv.
KEY_ISSEIGA = "is_seiga"
KEY_PIXIV_ID = "id"  # Key for Pixiv ID, used to create URL to pixiv image page, if applicable.
KEY_SEIGA_ID = "id"
PREFIX_PIXIV = "http://www.pixiv.net/member_illust.php?mode=medium&illust_id={}"
PREFIX_SEIGA = "http://seiga.nicovideo.jp/seiga/im{}"
SAVE_FOLDER = "data/lui-cogs/catgirl/"  # Path to save folder.
URL = "https://api.waifu.pics/sfw/neko"  # For a random sfw neko image from the waifu.pics API

EMPTY = {KEY_CATGIRL: [], KEY_CATBOY: []}
BASE = {
    "web": {
        KEY_CATGIRL: [
            {KEY_IMAGE_URL: "https://cdn.awwni.me/utpd.jpg", "id": "null", "is_pixiv": False}
        ],
        KEY_CATBOY: [],
    },
    "local": EMPTY,
    "localx10": EMPTY,
    "pending": EMPTY,
}

DEFAULT_GUILD = {"waifuneko": False}


class Catgirl(commands.Cog):  # pylint: disable=too-many-instance-attributes
    """Display cute nyaas~"""

    async def refreshDatabase(self):
        """Refreshes the JSON files"""
        # Local catgirls allow for prepending a domain if you have a place where
        # where you're hosting your own catgirls.
        # self.filepathLocal = SAVE_FOLDER + "links-local.json"
        # self.filepathLocalx10 = SAVE_FOLDER + "links-localx10.json"

        # Web catgirls will take on full URLs.
        # self.filepathWeb = SAVE_FOLDER + "links-web.json"

        # List of pending catgirls waiting to be added.
        # self.filepathPending = SAVE_FOLDER + "links-pending.json"

        self.picturesLocal = await self.config.local()
        self.picturesLocalx10 = await self.config.localx10()
        self.picturesWeb = await self.config.web()
        self.picturesPending = await self.config.pending()

        # Traps
        self.catgirlsLocalTrap = []

        # Prepend local listings with domain name.
        for image in self.picturesLocal[KEY_CATGIRL]:
            image[KEY_IMAGE_URL] = "https://nekomimi.injabie3.moe/p/" + image[KEY_IMAGE_URL]

            if "trap" in image and image["trap"]:
                self.catgirlsLocalTrap.append(image)

        # Prepend hosted listings with domain name.
        for image in self.picturesLocalx10[KEY_CATGIRL]:
            image[KEY_IMAGE_URL] = "http://injabie3.x10.mx/p/" + image[KEY_IMAGE_URL]

        for image in self.picturesLocal[KEY_CATBOY]:
            image[KEY_IMAGE_URL] = "http://nekomimi.injabie3.moe/p/b/" + image[KEY_IMAGE_URL]

        self.catgirlsLocal = self.picturesLocal[KEY_CATGIRL]

        self.catgirls = self.picturesLocal[KEY_CATGIRL]
        self.catgirls += self.picturesWeb[KEY_CATGIRL]
        self.catgirls += self.picturesLocalx10[KEY_CATGIRL]

        self.catboys = self.picturesLocal[KEY_CATBOY]
        self.catboys += self.picturesWeb[KEY_CATBOY]
        self.catboys += self.catgirlsLocalTrap

        self.pending = self.picturesPending[KEY_CATGIRL]

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647)
        self.config.register_global(**BASE)
        self.config.register_guild(**DEFAULT_GUILD)
        self.catgirls = None
        self.catgirlsLocal = None
        self.catgirlsLocalTrap = None
        self.catboys = None

        self.pending = None

        self.picturesLocal = None
        self.picturesLocalx10 = None
        self.picturesPending = None
        self.picturesWeb = None

    async def catgirlCmd(self, ctx):
        """Displays a random, cute catgirl :3"""
        # Send typing indicator, useful when Discord explicit filter is on.
        await ctx.channel.typing()
        nekoToggle = await self.config.guild(ctx.guild).waifuneko()

        if nekoToggle:
            choice = random.randint(0, 1)
            if choice == 0:
                embed = getImage(self.catgirls, "Catgirl")
            else:
                r = requests.get(url=URL)
                data = r.json()
                embed = getImageUrl(data["url"])
        else:
            embed = getImage(self.catgirls, "Catgirl")

        try:
            await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            # No permission to send, ignore.
            pass

    async def catboyCmd(self, ctx):
        """This command says it all (database still WIP)"""
        # Send typing indicator, useful when Discord explicit filter is on.
        await ctx.channel.typing()

        embed = getImage(self.catboys, "Catboy")

        try:
            await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            # No permission to send, ignore.
            pass

    # [p]catgirl
    @commands.command(name="catgirl")
    async def _catgirl(self, ctx):
        """Displays a random, cute catgirl :3"""
        await self.catgirlCmd(ctx)

    # [p]catboy
    @commands.command(name="catboy")
    async def _catboy(self, ctx):
        """This command says it all (database still WIP)"""
        await self.catboyCmd(ctx)

    @commands.group(name="nyaa")
    async def _nyaa(self, ctx):
        """Nekomimi universe!"""

    # [p]nyaa about
    @_nyaa.command(name="about")
    async def about(self, ctx):
        """Displays information about this module"""
        customAuthor = "[{}]({})".format("@Injabie3#1660", "https://injabie3.moe/")
        embed = discord.Embed()
        embed.title = "About this module"
        embed.add_field(name="Name", value="Catgirl Module")
        embed.add_field(name="Author", value=customAuthor)
        embed.add_field(name="Initial Version Date", value="2017-02-11")
        embed.add_field(
            name="Description",
            value="A module to display pseudo-random catgirl images.  Image "
            "links are stored in the local database, separated into different "
            "lists (depending on if they are hosted locally or on another "
            "domain).  See https://github.com/Injabie3/lui-cogs for more info.",
        )
        embed.set_footer(text="lui-cogs/catgirl")
        await ctx.send(embed=embed)

    # [p]nyaa catgirl
    @_nyaa.command(name="catgirl")
    async def catgirl(self, ctx):
        """Displays a random, cute catgirl :3"""
        await self.catgirlCmd(ctx)

    # [p]nyaa numbers
    @_nyaa.command(name="numbers")
    async def numbers(self, ctx):
        """Displays the number of images in the database."""
        msg = (
            "There are:\n"
            "- **{}** catgirls available.\n"
            "- **{}** catboys available.\n"
            "- **{}** pending images.".format(
                len(self.catgirls), len(self.catboys), len(self.picturesPending[KEY_CATGIRL])
            )
        )
        await ctx.send(msg)

    # [p]nyaa refresh - Also allow for refresh in a DM to the bot.
    @_nyaa.command(pass_context=True, no_pm=False)
    async def refresh(self, ctx):
        """Refreshes the internal database of nekomimi images."""
        await self.refreshDatabase()
        msg = (
            "List reloaded.  There are:\n"
            "- **{}** catgirls available.\n"
            "- **{}** catboys available.\n"
            "- **{}** pending images.".format(
                len(self.catgirls), len(self.catboys), len(self.picturesPending[KEY_CATGIRL])
            )
        )
        await ctx.send(msg)

    # [p]nyaa local
    @_nyaa.command(name="local")
    async def local(self, ctx):
        """Displays a random, cute catgirl from the local database."""
        # Send typing indicator, useful for when Discord explicit filter is on.
        await ctx.channel.typing()

        embed = getImage(self.catgirlsLocal, "Catgirl")

        try:
            await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            # No permission to send, ignore.
            pass

    # [p]nyaa trap
    @_nyaa.command(name="trap")
    async def trap(self, ctx):
        """Say no more fam, gotchu covered ;)"""
        # Send typing indicator, useful when Discord explicit filter is on.
        await ctx.channel.typing()

        embed = getImage(self.catgirlsLocalTrap, "Nekomimi")

        try:
            await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            # No permission to send, ignore.
            pass

    # [p]nyaa catboy
    @_nyaa.command(pass_context=True, no_pm=False)
    async def catboy(self, ctx):
        """Displays a random, cute catboy :3"""
        await self.catboyCmd(ctx)

    # [p] nyaa debug
    @_nyaa.command()
    async def debug(self, ctx):
        """Sends entire list via DM for debugging."""
        msg = "Debug Mode\nCatgirls:\n```"
        for image in self.catgirls:
            msg += image[KEY_IMAGE_URL] + "\n"
            if len(msg) > 1900:
                msg += "```"
                await ctx.message.author.send(msg)
                msg = "```"
        msg += "```"
        await ctx.message.author.send(msg)

        msg = "Catboys:\n```"
        for image in self.catboys:
            msg += image[KEY_IMAGE_URL] + "\n"
            if len(msg) > 1900:
                msg += "```"
                await ctx.message.author.send(msg)
                msg = "```"
        msg += "```"
        await ctx.message.author.send(msg)

    # [p]nyaa add
    @commands.guild_only()
    @_nyaa.command(name="add")
    async def add(self, ctx, link: str, description: str = ""):
        """Add a catgirl image to the pending database.
        Will be screened before it is added to the global list. WIP

        link          The full URL to an image, use \" \" around the link.
        description   Description of character (optional)
        """

        temp = {}
        temp["url"] = link
        temp["character"] = description
        temp["submitter"] = ctx.message.author.name
        temp["id"] = None
        temp["is_pixiv"] = False

        self.picturesPending[KEY_CATGIRL].append(temp)
        await self.config.pending.put(self.picturesPending)

        # Get owner ID.
        owner = discord.utils.get(self.bot.get_all_members(), id=self.bot.owner_id)

        try:
            await owner.send("New catgirl image is pending approval. Please check " "the list!")
        except discord.errors.InvalidArgument:
            await ctx.send("Added, but could not notify owner.")
        else:
            await ctx.send("Added, notified and pending approval. :ok_hand:")

    # [p]nyaa toggle
    @_nyaa.command(name="toggle")
    @checks.mod_or_permissions(manage_guild=True)
    async def toggle(self, ctx):
        """Toggle using waifu.pics API"""
        # Send typing indicator, useful when Discord explicit filter is on.
        await ctx.channel.typing()

        waifuneko_val = await self.config.guild(ctx.guild).waifuneko()
        await self.config.guild(ctx.guild).waifuneko.set(False if waifuneko_val else True)

        await ctx.send(
            "Using waifupics API for catgirls is now {}".format("off" if waifuneko_val else "on")
        )  # waifuneko_val wasn't updated after setting the thing

    async def randomize(self):
        """Shuffles images in the list."""
        while self:
            random.shuffle(self.catgirls)
            random.shuffle(self.catboys)
            random.shuffle(self.catgirlsLocal)
            await asyncio.sleep(3600)


def getImage(imageList, title):
    """Pick an image from a list, and construct a discord.Embed object

    Parameters:
    -----------
    imageList : []
        A list of images that has the following keys:
        KEY_IMAGE_URL, KEY_ISPIXIV, KEY_ISSEIGA

    Returns:
    --------
    embed : discord.Embed
        A fully constructed discord.Embed object, ready to be sent as a message.
    """
    image = random.choice(imageList)
    embed = discord.Embed()
    embed.colour = discord.Colour.red()
    embed.title = title
    embed.url = image[KEY_IMAGE_URL].replace(" ", "%20")
    if KEY_ISPIXIV in image and image[KEY_ISPIXIV]:
        source = "[{}]({})".format("Original Source", PREFIX_PIXIV.format(image[KEY_PIXIV_ID]))
        embed.add_field(name="Pixiv", value=source)
        customFooter = "ID: " + image[KEY_PIXIV_ID]
        embed.set_footer(text=customFooter)
    elif KEY_ISSEIGA in image and image[KEY_ISSEIGA]:
        source = "[{}]({})".format("Original Source", PREFIX_SEIGA.format(image[KEY_SEIGA_ID]))
        embed.add_field(name="Nico Nico Seiga", value=source)
        customFooter = "ID: {}".format(image[KEY_SEIGA_ID])
        embed.set_footer(text=customFooter)
    # Implemented the following with the help of
    # http://stackoverflow.com/questions/1602934/
    if "character" in image:
        embed.add_field(name="Info", value=image["character"], inline=False)
    embed.set_image(url=image[KEY_IMAGE_URL])
    return embed


def getImageUrl(image):
    """
    Take a passed url from Waifu.pics, and construct a discord.Embed object

    Parameters:
    -----------
    image : a URL

    Returns:
    -----------
    embed : discord.embed
        a fully constructed discord.Embed object, ready to be sent as a message.
    """
    embed = discord.Embed()
    embed.colour = discord.Colour.red()
    embed.title = "Catgirl"
    embed.url = image
    embed.set_image(url=image)
    return embed
