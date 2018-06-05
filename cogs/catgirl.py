import discord
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
import asyncio #Used for task loop.
import os #Used to create folder at first load.
import random #Used for selecting random catgirls.

#Global variables
JSON_mainKey = "catgirls" #Key for JSON files.
JSON_catboyKey = "catboys" #Key containing other images.
JSON_imageURLKey = "url" #Key for URL
JSON_isPixiv = "is_pixiv" #Key that specifies if image is from pixiv. If true, pixivID should be set.
JSON_isSeiga = "is_seiga"
JSON_pixivID = "id" #Key for Pixiv ID, used to create URL to pixiv image page, if applicable.
JSON_seigaID = "id"
saveFolder = "data/lui-cogs/catgirl/" #Path to save folder.

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(saveFolder):
        print("Creating " + saveFolder + " folder...")
        os.makedirs(saveFolder)

def checkFiles():
    """Used to initialize an empty database at first startup"""
    base = { JSON_mainKey : [{ JSON_imageURLKey :"https://cdn.awwni.me/utpd.jpg" , "id" : "null", "is_pixiv" : False}], JSON_catboyKey : [] }
    empty = { JSON_mainKey : [], JSON_catboyKey : [] }
    
    f = saveFolder + "links-web.json"
    if not dataIO.is_valid_json(f):
        print("Creating default catgirl links-web.json...")
        dataIO.save_json(f, base)
        
    f = saveFolder + "links-localx10.json"
    if not dataIO.is_valid_json(f):
        print("Creating default catgirl links-localx10.json...")
        dataIO.save_json(f, empty)
        
    f = saveFolder + "links-local.json"
    if not dataIO.is_valid_json(f):
        print("Creating default catgirl links-local.json...")
        dataIO.save_json(f, empty)
        
    f = saveFolder + "links-pending.json"
    if not dataIO.is_valid_json(f):
        print("Creating default catgirl links-pending.json...")
        dataIO.save_json(f, empty)
            
class Catgirl_beta:
    """Display cute nyaas~"""


    def refreshDatabase(self):
        """Refreshes the JSON files"""
        #Local catgirls allow for prepending predefined domain, if you have a place where you're hosting your own catgirls.
        self.filepath_local = saveFolder + "links-local.json"
        self.filepath_localx10 = saveFolder + "links-localx10.json"
        
        #Web catgirls will take on full URLs.
        self.filepath_web = saveFolder + "links-web.json"

        #List of pending catgirls waiting to be added.
        self.filepath_pending = saveFolder + "links-pending.json"
        
        #Catgirls
        self.pictures_local = dataIO.load_json(self.filepath_local)
        self.pictures_localx10 = dataIO.load_json(self.filepath_localx10)
        self.pictures_web = dataIO.load_json(self.filepath_web)
        self.pictures_pending = dataIO.load_json(self.filepath_pending)
        
        #Trap (kek)
        self.catgirls_local_trap = [];

        #Custom key which holds an array of catgirl filenames/paths
        self.JSON_mainKey = "catgirls"
        
        #Prepend local listings with domain name.
        for x in range(0,len(self.pictures_local[JSON_mainKey])):
            self.pictures_local[JSON_mainKey][x][JSON_imageURLKey] = "https://nekomimi.injabie3.moe/p/" + self.pictures_local[JSON_mainKey][x][JSON_imageURLKey]

            if ("trap" in self.pictures_local[JSON_mainKey][x]) and (self.pictures_local[JSON_mainKey][x]['trap'] is True):
                self.catgirls_local_trap.append(self.pictures_local[JSON_mainKey][x])
            #self.pictures_local[JSON_mainKey][x][JSON_imageURLKey] = "https://nyan.injabie3.moe/p/" + self.pictures_local[JSON_mainKey][x][JSON_imageURLKey]

        #Prepend hosted listings with domain name.
        for x in range(0,len(self.pictures_localx10[JSON_mainKey])):
            self.pictures_localx10[JSON_mainKey][x][JSON_imageURLKey] = "http://injabie3.x10.mx/p/" + self.pictures_localx10[JSON_mainKey][x][JSON_imageURLKey]
        
        for x in range(0, len(self.pictures_local[JSON_catboyKey])):
            self.pictures_local[JSON_catboyKey][x][JSON_imageURLKey] = "http://nekomimi.injabie3.moe/p/b/" + self.pictures_local[JSON_catboyKey][x][JSON_imageURLKey]

        self.catgirls_local = self.pictures_local[JSON_mainKey]
        self.catgirls = self.pictures_local[JSON_mainKey] + self.pictures_web[JSON_mainKey] + self.pictures_localx10[JSON_mainKey]
        self.catboys = self.pictures_local[JSON_catboyKey] + self.pictures_web[JSON_catboyKey] + self.catgirls_local_trap
        self.pending = self.pictures_pending[JSON_mainKey]
        
    def __init__(self, bot):
        self.bot = bot
        checkFolder()
        checkFiles()
        self.refreshDatabase()
        
    #[p]catgirl
    @commands.command(name="catgirl", pass_context=True)
    async def _catgirl(self, ctx):
        """Displays a random, cute catgirl :3"""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatgirl = random.choice(self.catgirls)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Catgirl"+randCatgirl[JSON_pixivID]
        embed.url = randCatgirl[JSON_imageURLKey]
        if JSON_isPixiv in randCatgirl and randCatgirl[JSON_isPixiv]:
            source = "[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatgirl[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatgirl[JSON_pixivID]
            embed.set_footer(text=customFooter)
        if JSON_isSeiga in randCatgirl and randCatgirl[JSON_isSeiga]:
            source = "[{}]({})".format("Original Source","http://seiga.nicovideo.jp/seiga/im"+randCatgirl[JSON_seigaID])
            embed.add_field(name="Nico Nico Seiga",value=source)
            customFooter = "ID: " + randCatgirl[JSON_seigaID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatgirl:
            embed.add_field(name="Info",value=randCatgirl["character"], inline=False)
        embed.set_image(url=randCatgirl[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(randCatgirl)
            print(e)
            print("==========")

    #[p]catboy
    @commands.command(name="catboy", pass_context=True)
    async def _catboy(self, ctx):
        """This command says it all (database still WIP)"""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatboy = random.choice(self.catboys)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Catboy"
        embed.url = randCatboy[JSON_imageURLKey]
        if randCatboy[JSON_isPixiv]:
            source="[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatboy[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatboy[JSON_pixivID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatboy:
            embed.add_field(name="Info",value=randCatboy["character"], inline=False)
        embed.set_image(url=randCatboy[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(randCatboy)
            print(e)
            print("==========")

    @commands.group(name="nyaa", pass_context=True, no_pm=False)
    async def _nyaa(self, ctx):
        """Nekomimi universe! \o/"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    #[p]nyaa about
    @_nyaa.command(pass_context=True, no_pm=False)
    async def about(self, ctx):
        """Displays information about this module"""
        customAuthor = "[{}]({})".format("@Injabie3#1660","https://injabie3.moe/")
        embed = discord.Embed()
        embed.title = "About this module"
        embed.add_field(name="Name", value="Catgirl Module")
        embed.add_field(name="Author", value=customAuthor)
        embed.add_field(name="Initial Version Date", value="2017-02-11")
        embed.add_field(name="Description", value="A module to display pseudo-random catgirl images.  Image links are stored in the local database, separated into different lists (depending on if they are hosted locally or on another domain).  See https://github.com/Injabie3/lui-cogs for more info.")
        embed.set_footer(text="lui-cogs/catgirl")
        await self.bot.say(content="",embed=embed)

    #[p]nyaa catgirl
    @_nyaa.command(pass_context=True, no_pm=False)
    async def catgirl(self, ctx):
        """Displays a random, cute catgirl :3"""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatgirl = random.choice(self.catgirls)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Catgirl"
        embed.url = randCatgirl[JSON_imageURLKey]
        if JSON_isPixiv in randCatgirl and randCatgirl[JSON_isPixiv]:
            source = "[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatgirl[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatgirl[JSON_pixivID]
            embed.set_footer(text=customFooter)
        if JSON_isSeiga in randCatgirl and randCatgirl[JSON_isSeiga]:
            source = "[{}]({})".format("Original Source","http://seiga.nicovideo.jp/seiga/im"+randCatgirl[JSON_seigaID])
            embed.add_field(name="Nico Nico Seiga",value=source)
            customFooter = "ID: " + randCatgirl[JSON_seigaID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatgirl:
            embed.add_field(name="Info",value=randCatgirl["character"], inline=False)
        embed.set_image(url=randCatgirl[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(randCatgirl)
            print(e)
            print("==========")
        
    #[p]nyaa numbers
    @_nyaa.command(pass_context=True, no_pm=False)
    async def numbers(self, ctx):
        """Displays the number of images in the database."""
        await self.bot.say("There are:\n - **" + str(len(self.catgirls)) + "** catgirls available.\n - **" + str(len(self.catboys)) + "** catboys available.\n - **" + str(len(self.pictures_pending[JSON_mainKey])) + "** pending images.")

    #[p]nyaa refresh - Also allow for refresh in a DM to the bot.
    @_nyaa.command(pass_context=True, no_pm=False)
    async def refresh(self, ctx):
        """Refreshes the internal database of nekomimi images."""
        self.refreshDatabase()
        await self.bot.say("List reloaded.  There are:\n - **" + str(len(self.catgirls)) + "** catgirls available.\n - **" + str(len(self.catboys)) + "** catboys available.\n - **" + str(len(self.pictures_pending[JSON_mainKey])) + "** pending images.")
    
    #[p]nyaa local
    @_nyaa.command(pass_context=True, no_pm=False)
    async def local(self, ctx):
        """Displays a random, cute catgirl from the local database."""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatgirl = random.choice(self.catgirls_local)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Catgirl"
        embed.url = randCatgirl[JSON_imageURLKey]
        if randCatgirl[JSON_isPixiv]:
            source="[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatgirl[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatgirl[JSON_pixivID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatgirl:
            embed.add_field(name="Info",value=randCatgirl["character"], inline=False)
        embed.set_image(url=randCatgirl[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(randCatgirl)
            print(e)
            print("==========")

    #[p]nyaa trap
    @_nyaa.command(pass_context=True, no_pm=False)
    async def trap(self, ctx):
        """Say no more fam, gotchu covered ;)"""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatgirl = random.choice(self.catgirls_local_trap)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Nekomimi"
        embed.url = randCatgirl[JSON_imageURLKey]
        if randCatgirl[JSON_isPixiv]:
            source="[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatgirl[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatgirl[JSON_pixivID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatgirl:
            embed.add_field(name="Info",value=randCatgirl["character"], inline=False)
        embed.set_image(url=randCatgirl[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(e)
            print("==========")

    #[p]nyaa catboy
    @_nyaa.command(pass_context=True, no_pm=False)
    async def catboy(self, ctx):
        """Displays a random, cute catboy :3"""
        #Send typing indicator, useful for when Discord explicit filter is on.
        await self.bot.send_typing(ctx.message.channel)

        randCatboy = random.choice(self.catboys)
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = "Catboy"
        embed.url = randCatboy[JSON_imageURLKey]
        if randCatboy[JSON_isPixiv]:
            source="[{}]({})".format("Original Source","http://www.pixiv.net/member_illust.php?mode=medium&illust_id="+randCatboy[JSON_pixivID])
            embed.add_field(name="Pixiv",value=source)
            customFooter = "ID: " + randCatboy[JSON_pixivID]
            embed.set_footer(text=customFooter)
        #Implemented the following with the help of http://stackoverflow.com/questions/1602934/check-if-a-given-key-already-exists-in-a-dictionary
        if "character" in randCatboy:
            embed.add_field(name="Info",value=randCatboy["character"], inline=False)
        embed.set_image(url=randCatboy[JSON_imageURLKey])
        try:
            await self.bot.say("",embed=embed)
        except Exception as e:
            await self.bot.say("Please try again.")
            print("Catgirl exception:")
            print(e)
            print("==========")

    #[p] nyaa debug
    @_nyaa.command(pass_context=True, no_pm=False)
    async def debug(self, ctx):
        """Sends entire list via DM for debugging."""
        msg = "Debug Mode\nCatgirls:\n```"
        for x in range(0,len(self.catgirls)):
            msg += self.catgirls[x][JSON_imageURLKey] + "\n"
            if len(msg) > 1900:
               msg += "```"
               await self.bot.send_message(ctx.message.author, msg)
               msg = "```"
        msg += "```"
        await self.bot.send_message(ctx.message.author, msg)
        
        msg = "Catboys:\n```"
        for x in range(0,len(self.catboys)):
            msg += self.catboys[x][JSON_imageURLKey] + "\n"
            if len(msg) > 1900:
               msg += "```"
               await self.bot.send_message(ctx.message.author, msg)
               msg = "```"
        msg += "```"
        await self.bot.send_message(ctx.message.author, msg)
    
    #[p]nyaa add
    @_nyaa.command(pass_context=True, no_pm=True)
    async def add(self, ctx, link: str, description: str=""):
        """
        Add a catgirl image to the pending database.
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
        
    
        self.pictures_pending[JSON_mainKey].append(temp)
        dataIO.save_json(self.filepath_pending, self.pictures_pending)

        #Get owner ID.
        owner = discord.utils.get(self.bot.get_all_members(),id=self.bot.settings.owner)
                              
        try:
            await self.bot.send_message(owner, "New catgirl image is pending approval. Please check the list!")
        except discord.errors.InvalidArgument:
            await self.bot.say("Added, but could not notify owner.")
        else:
            await self.bot.say("Added, notified and pending approval. :ok_hand:")
                
        
            
    async def _randomize(self):
        """Shuffles images in the list."""
        while self:
            random.shuffle(self.catgirls)
            random.shuffle(self.catboys)
            random.shuffle(self.catgirls_local)
            await asyncio.sleep(3600)

def setup(bot):
    checkFolder()   #Make sure the data folder exists!
    checkFiles()    #Make sure we have a local database!
    nyanko = Catgirl_beta(bot)
    bot.add_cog(nyanko)
    bot.loop.create_task(nyanko._randomize())
