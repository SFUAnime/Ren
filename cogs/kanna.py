import discord
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
import os #For folder creation
import random #Used for selecting random kannas

#Global variables
JSON_mainKey = "kanna" #Key for JSON files.
JSON_imageURLKey = "url" #Key for URL
JSON_isPixiv = "is_pixiv"
JSON_pixivID = "id"
saveFolder = "data/lui-cogs/kanna/" #Path to save folder.

def checkFolder():
    if not os.path.exists(saveFolder):
        print("Creating " + saveFolder + " folder...")
        os.makedirs(saveFolder)
		
def checkFiles():
    """Used to initialize an empty database at first startup"""
    base = { JSON_mainKey : [{ JSON_imageURLKey : "http://68.media.tumblr.com/31a2526f30f240567fb2203992c0d8f1/tumblr_olmpzbJaul1vdwiwto1_400.gif" , "id" : "null", "is_pixiv" : False}] }

    f = saveFolder + "links-web.json"
    if not dataIO.is_valid_json(f):
        print("Creating default kanna links-web.json...")
        dataIO.save_json(f, base)

    f = saveFolder + "links-localx10.json"
    if not dataIO.is_valid_json(f):
        print("Creating default kanna links-localx10.json...")
        dataIO.save_json(f, { JSON_mainKey : []})

    f = saveFolder + "links-local.json"
    if not dataIO.is_valid_json(f):
        print("Creating default kanna links-local.json...")
        dataIO.save_json(f, { JSON_mainKey : []})

class Kanna_beta:
    """Display cute kannas~"""


    def refreshDatabase(self):
        """Refreshes the JSON files"""
        #Local kannas allow for prepending predefined domain, if you have a place where you're hosting your own kannas.
        self.filepath_local = saveFolder + "links-local.json"
        self.filepath_localx10 = saveFolder + "links-localx10.json"
        
        #Web kannas will take on full URLs.
        self.filepath_web = saveFolder + "links-web.json"
        
        self.pictures_local = dataIO.load_json(self.filepath_local)
        self.pictures_localx10 = dataIO.load_json(self.filepath_localx10)
        self.pictures_web = dataIO.load_json(self.filepath_web)   
                
        #Prepend local listings with domain name.
        for x in range(0,len(self.pictures_local[JSON_mainKey])):
            self.pictures_local[JSON_mainKey][x][JSON_imageURLKey] = "https://nekomimi.injabie3.moe/p/" + self.pictures_local[JSON_mainKey][x][JSON_imageURLKey]
        for x in range(0,len(self.pictures_localx10[JSON_mainKey])):
            self.pictures_localx10[JSON_mainKey][x][JSON_imageURLKey] = "http://injabie3.x10.mx/p/" + self.pictures_localx10[JSON_mainKey][x][JSON_imageURLKey]


        self.kanna_local = self.pictures_local[JSON_mainKey]
        self.kanna = self.pictures_local[JSON_mainKey] + self.pictures_web[JSON_mainKey] + self.pictures_localx10[JSON_mainKey]

    def __init__(self, bot):
        self.bot = bot
        checkFolder()
        checkFiles()
        self.refreshDatabase()
        
    #@commands.command(name="kanna")
    #async def _kanna(self):

    @commands.group(name="kanna", pass_context=True, no_pm=False)
    async def _kanna(self, ctx):
        """Displays a random, cute kanna :3"""
        if ctx.invoked_subcommand is None:
        #    await send_cmd_help(ctx)
            randKanna = random.choice(self.kanna)
            embed = discord.Embed()
            embed.colour = discord.Colour.purple()
            embed.title = "Kanna"
            embed.url = randKanna[JSON_imageURLKey]
            if randKanna[JSON_isPixiv]:
                source="[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randKanna[JSON_pixivID])
                embed.add_field(name="Pixiv",value=source)
                customFooter = "ID: " + randKanna[JSON_pixivID]
                embed.set_footer(text=customFooter)
            embed.set_image(url=randKanna[JSON_imageURLKey])
            await self.bot.say("",embed=embed)

    #[p]kanna about
    @_kanna.command(pass_context=True, no_pm=False)
    async def about(self, ctx):
        """Displays information about this module"""
        customAuthor = "[{}]({})".format("@Injabie3#1660","https://injabie3.moe/")
        embed = discord.Embed()
        embed.title = "About this module"
        embed.add_field(name="Name", value="Kanna Module")
        embed.add_field(name="Author", value=customAuthor)
        embed.add_field(name="Initial Version Date", value="2017-02-20")
        embed.add_field(name="Description", value="Literally a copy of the Catgirl Module, except for Kanna images only. See https://github.com/Injabie3/lui-cogs for more info")
        embed.set_footer(text="lui-cogs/kanna")
        await self.bot.say(content="",embed=embed)
        

    #[p]kanna numbers
    @_kanna.command(pass_context=True, no_pm=False)
    async def numbers(self, ctx):
        """Displays the number of Kanna images on file."""
        await self.bot.say("There are " + str(len(self.kanna)) + " Kanna images available at the moment!")

    #[p]kanna refresh
    @_kanna.command(pass_context=True, no_pm=False)
    async def refresh(self, ctx):
        """Refreshes the internal database of Kanna images."""
        self.refreshDatabase()
        await self.bot.say("List reloaded. There are " + str(len(self.kanna)) + " Kanna images available.")

    #[p] kanna debug
    @_kanna.command(pass_context=True, no_pm=False)
    async def debug(self, ctx):
        """Debug to see if list is okay"""
        msg = "Debug Mode\n```"
        for x in range(0,len(self.kanna)):
            msg += self.kanna[x][JSON_imageURLKey] + "\n"
            if len(msg) > 900:
               msg += "```"
               await self.bot.say(msg)
               msg = "```"
        msg += "```"
        await self.bot.say(msg)
        #await self.bot.say("This feature is disabled.")


def setup(bot):
    checkFolder()	#Make sure the data folder exists!
    checkFiles()	#Make sure we have a local database!
    bot.add_cog(Kanna_beta(bot))
