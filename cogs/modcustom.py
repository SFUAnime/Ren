import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help, settings
from collections import deque, defaultdict
from cogs.utils.chat_formatting import escape_mass_mentions, box
import os
import re
import logging
import asyncio

def check_folders():
    folders = ("data", "data/modcustom/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    blacklist_list = {"users": [], "roles": []}
    whitelist_list = {"users": [], "roles": []}

    files = {
        "blacklist.json"      : blacklist_list,
        "whitelist.json"      : whitelist_list
    }

    for filename, value in files.items():
        if not os.path.isfile("data/modcustom/{}".format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json("data/modcustom/{}".format(filename), value)


class ModCustom(object):
    """Custom mod tools for use outside of the standard Ren-bot Framework"""
    
    def __init__(self, bot):
        self.bot = bot
        self.whitelist_list = dataIO.load_json("data/modcustom/whitelist.json")
        self.blacklist_list = dataIO.load_json("data/modcustom/blacklist.json")
        
    def is_plonked(self, server, member): # note: message.server isnt needed
        if len([x for x in self.blacklist_list["users"] if member.id == x ]) == 0:
            return False
        else:
            return True
    
    def has_perms(self, server, member):
        perms = []
        overrides = [] # these roles have higher precedence than blacklist roles
        for role in member.roles:
            perms += [x for x in self.blacklist_list["roles"] if x in role.name]
            overrides += [x for x in self.whitelist_list["roles"] if x in role.name]
            
        if len(perms) == 0: # no blacklisted roles, we good to go
            return True
        elif len(perms) != 0 and len(overrides) != 0: # have a blacklisted role, but also have a whitelisted role, good to go
            return True
        else: # sorry, better luck next time
            return False
            
    @commands.group(pass_context=True)
    @checks.is_owner_or_permissions(administrator=True)
    async def m_blacklist(self, ctx):
        """Bans user from using the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @m_blacklist.command(name="adduser")
    async def _blacklist_adduser(self, user: discord.Member):
        """Adds user to bot's blacklist"""
        if user.id not in self.blacklist_list["users"]:
            self.blacklist_list["users"].append(user.id)
            dataIO.save_json("data/modcustom/blacklist.json", self.blacklist_list)
            await self.bot.say("User has been added to blacklist.")
        else:
            await self.bot.say("User is already blacklisted.")

    @m_blacklist.command(name="addrole")
    async def _blacklist_addrole(self, role: str):
        """Adds role to bot's blacklist"""
        if role not in self.blacklist_list["roles"]:
            self.blacklist_list["roles"].append(role)
            dataIO.save_json("data/modcustom/blacklist.json", self.blacklist_list)
            await self.bot.say("Role has been added to blacklist.")
        else:
            await self.bot.say("Role is already blacklisted.")
            
    @m_blacklist.command(name="removeuser")
    async def _blacklist_removeuser(self, user: discord.Member):
        """Removes user from bot's blacklist"""
        if user.id in self.blacklist_list["users"]:
            self.blacklist_list["users"].remove(user.id)
            dataIO.save_json("data/modcustom/blacklist.json", self.blacklist_list)
            await self.bot.say("User has been removed from blacklist.")
        else:
            await self.bot.say("User is not in blacklist.")

    @m_blacklist.command(name="removerole")
    async def _blacklist_removerole(self, role: str):
        """Removes role to bot's blacklist"""
        if role in self.blacklist_list["roles"]:
            self.blacklist_list["roles"].remove(role)
            dataIO.save_json("data/modcustom/blacklist.json", self.blacklist_list)
            await self.bot.say("Role has been removed from blacklist.")
        else:
            await self.bot.say("Role is not in blacklist.")
            
    @m_blacklist.command(name="clear")
    async def _blacklist_clear(self):
        """Clears the blacklist"""
        self.blacklist_list = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/blacklist.json", self.blacklist_list)
        await self.bot.say("Blacklist is now empty.")

    @commands.group(pass_context=True)
    @checks.is_owner_or_permissions(administrator=True)
    async def m_whitelist(self, ctx):
        """Users who will be able to use the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @m_whitelist.command(name="adduser")
    async def _whitelist_adduser(self, user: discord.Member):
        """Adds user to bot's whitelist"""
        if user.id not in self.whitelist_list["users"]:
            if not self.whitelist_list["users"]:
                msg = "\nAll users not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.whitelist_list["users"].append(user.id)
            dataIO.save_json("data/modcustom/whitelist.json", self.whitelist_list)
            await self.bot.say("User has been added to whitelist." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @m_whitelist.command(name="addrole")
    async def _whitelist_addrole(self, role: str):
        """Adds role to bot's whitelist"""
        if role not in self.whitelist_list["roles"]:
            if not self.whitelist_list["roles"]:
                msg = "\nAll roles not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.whitelist_list["roles"].append(role)
            dataIO.save_json("data/modcustom/whitelist.json", self.whitelist_list)
            await self.bot.say("Role has been added to whitelist." + msg)
        else:
            await self.bot.say("Role is already whitelisted.")

    @m_whitelist.command(name="removeuser")
    async def _whitelist_removeuser(self, user: discord.Member):
        """Removes user from bot's whitelist"""
        if user.id in self.whitelist_list["users"]:
            self.whitelist_list["users"].remove(user.id)
            dataIO.save_json("data/modcustom/whitelist.json", self.whitelist_list)
            await self.bot.say("User has been removed from whitelist.")
        else:
            await self.bot.say("User is not in whitelist.")

    @m_whitelist.command(name="removerole")
    async def _whitelist_removerole(self, role: str):
        """Adds role to bot's whitelist"""
        if role in self.whitelist_list["roles"]:
            self.whitelist_list["roles"].remove(role)
            dataIO.save_json("data/modcustom/whitelist.json", self.whitelist_list)
            await self.bot.say("Role has been removed from whitelist.")
        else:
            await self.bot.say("Role is not in whitelist.")
    
    @m_whitelist.command(name="clear")
    async def _whitelist_clear(self):
        """Clears the whitelist"""
        self.whitelist_list = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/whitelist.json", self.whitelist_list)
        await self.bot.say("Whitelist is now empty.")
        
def setup(bot):
    check_folders()
    check_files()
    n = ModCustom(bot)
    bot.add_cog(n)