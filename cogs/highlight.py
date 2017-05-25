import discord
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
import asyncio
import aiohttp
from datetime import datetime
import os
import itertools

"""
Cogs Purpose: To dm a user certain "highlight" words that they specify
Requirements:

Credit: This idea was first implemented by Danny (https://github.com/Rapptz/) but that bot is currently closed source.
        So this is my own, and most definitely subpar, implementation of highlights
"""

def check_filesystem():

    folders = ["data/highlight"]
    for folder in folders:
        if not os.path.exists(folder):
            print("Highlight: Creating folder: {} ...".format(folder))
            os.makedirs(folder)
            
    files = ["data/highlight/words.json"]
    for file in files:
        if not os.path.exists(file):
            if "words" in file:
                #build a default words.json
                dict = {}
                default = {}
                users = {}
                user = {}
                users['users'] = []
                user['id'] = 123456789
                user['words'] = ["one", "two", "three", "four", "five"]
                users['users'].append(user)
                default['123456789'] = users
                dict['guilds'] = []
                dict['guilds'].append(default)
                dataIO.save_json("data/highlight/words.json",dict)
                
            print("Highlight: Creating file: {} ...".format(file))
            
class Highlight(object):
    def __init__(self, bot):
        self.bot = bot
        self.highlights = dataIO.load_json("data/highlight/words.json")
    
    def _check_guilds(self, guild_id):
        """returns guild pos in list"""
        guilds = [list(x) for x in self.highlights['guilds']]
        guilds_ids = list(itertools.chain.from_iterable(guilds)) # flatten list
        
        if guild_id not in guilds_ids:
            new_guild = {}
            users = {}
            users['users'] = []
            new_guild[guild_id] = users
            self.highlights['guilds'].append(new_guild)
            dataIO.save_json("data/highlight/words.json", self.highlights)
            self.highlights = dataIO.load_json("data/highlight/words.json")
            
        return next(x for (x,d) in enumerate(self.highlights['guilds']) if guild_id in d)
    
    def _is_registered(self, guild_idx, guild_id, user_id):
        users = self.highlights['guilds'][guild_idx][guild_id]['users']

        for user in users:
            if user_id == user['id']:
                user_add = user        
                return [next(index for (index, d) in enumerate(users) if d["id"] == user['id']), user_add]
        return None
    
    @commands.group(name="highlight", pass_context=True, no_pm=True)
    async def highlight(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
        
    @highlight.command(name="add", pass_context=True, no_pm=True)
    async def add_highlight(self, ctx, word: str):
        guild_id = ctx.message.server.id
        user_id = ctx.message.author.id
        user_name = ctx.message.author.name
        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)
        
        if user is not None:
            user_idx = user[0]
            user_add = user[1]
            if len(user_add['words']) <= 4: # user can only have max of 5 words
                user_add['words'].append(word)
                self.highlights['guilds'][guild_idx][guild_id]['users'][user_idx] = user_add
                dataIO.save_json("data/highlight/words.json", self.highlights)
                t_msg = await self.bot.say("Highlight word added, {}".format(user_name))
                await asyncio.sleep(2)
                await self.bot.delete_message(t_msg)
            else:
                t_msg = await self.bot.say("Sorry {}, you already have 5 words highlighted".format(user_name))
                await asyncio.sleep(2)
                await self.bot.delete_message(t_msg)
        else:
            new_user = {}
            new_user['id'] = ctx.message.author.id
            new_user['words'] = [word]
            self.highlights['guilds'][guild_idx][guild_id]['users'].append(new_user)
            dataIO.save_json("data/highlight/words.json", self.highlights)
            
        self.highlights = dataIO.load_json("data/highlight/words.json")
        
    @highlight.command(name="remove", pass_context=True, no_pm=True)
    async def remove_highlight(self, ctx, word: str):
        guild_id = ctx.message.server.id
        user_id = ctx.message.author.id
        user_name = ctx.message.author.name
        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)
        
        if user is not None:
            user_idx = user[0]
            user_rm = user[1]
            if word in user_rm['words']:
                user_rm['words'].remove(word)
                self.highlights['guilds'][guild_idx][guild_id]['users'][user_idx] = user_rm
                dataIO.save_json("data/highlight/words.json", self.highlights)
                t_msg = await self.bot.say("Highlight word removed, {}".format(user_name))
                await asyncio.sleep(2)
                await self.bot.delete_message(t_msg)
            else:
                t_msg = await self.bot.say("Sorry {}, you don't have this word highlighted".format(user_name))
                await asyncio.sleep(2)
                await self.bot.delete_message(t_msg)
        else:
            msg = "Sorry {}, you aren't currently registered for highlights."
            msg += " Add a word to become registered"
            t_msg = await self.bot.say(msg.format(user_name))
            await asyncio.sleep(2)
            await self.bot.delete_message(t_msg)
            
        self.highlights = dataIO.load_json("data/highlight/words.json")
        
    @highlight.command(name="list", pass_context=True, no_pm=True)
    async def list_highlight(self, ctx):
        guild_id = ctx.message.server.id
        user_id = ctx.message.author.id
        user_name = ctx.message.author.name
        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)
        
        if user is not None:
            user_list = user[1]
            if len(user_list['words']) > 0:
                msg = ""
                for word in user_list['words']:
                    msg += word
                    msg += "\n"
                    
                embed = discord.Embed(description=msg,colour=discord.Colour.red())
                embed.set_author(name=ctx.message.author.name,icon_url=ctx.message.author.avatar_url)
                temp_msg = await self.bot.say(embed=embed)
                await asyncio.sleep(5)
                await self.bot.delete_message(temp_msg)
            else:
                t_msg = await self.bot.say("Sorry {}, you have no highlighted words currently".format(user_name))
                await asyncio.sleep(2)
                await self.bot.delete_message(t_msg)
            
    @highlight.command(name="import", pass_context=True, no_pm=False)
    async def import_highlight(self, ctx, from_server: str):
        #do some sort of  utils.get to find guild id
        pass
    
    async def check_highlights(self, msg):
        """
        1. check if the msg is in any of any users words
        2. if it was, get 5-6 messages AROUND the msg
        3. construct some metadata based off this info
        4. format a message, send to DM
        """
        if isinstance(msg.channel,discord.PrivateChannel):
            return
            
        guild_id = msg.server.id
        user_id = msg.author.id
        user_name = msg.author.name
        user_obj = msg.author
        guild_idx = self._check_guilds(guild_id)
        user = self._is_registered(guild_idx,guild_id,user_id)
        
        if user is not None:
            user_words = user[1]['words']
            for word in user_words:
                if word in msg.content:
                    await self._notify_user(user_obj,msg,word)
                    
    async def _notify_user(self, user, message, word):
        msgs = []
        async for msg in self.bot.logs_from(message.channel,limit=10,around=message):
            msgs.append(msg)
        msg_ctx = sorted(msgs, key=lambda r: r.timestamp)
        notify_msg = "In <#{1.channel.id}>, you were mentioned with highlight word **{0}**:\n".format(word,message)
        for msg in msg_ctx:
            time = msg.timestamp.isoformat(' ')
            notify_msg += "[{0}] {1.author.name}#{1.author.discriminator}: {1.content}\n".format(time,msg)
        await self.bot.send_message(user,notify_msg)
        
    async def _last_spoken(self):
        pass # TODO: check if user sent message in last 10 seconds or so, if so dont send a PM
    
def setup(bot):
    check_filesystem()
    hilite = Highlight(bot)
    bot.add_listener(hilite.check_highlights, 'on_message')
    bot.add_cog(hilite)
    