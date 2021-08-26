import discord
from discord.ext import commands
import functools


async def check_permissions(ctx, perms):
    if await ctx.bot.is_owner(ctx.author):
        return True
    elif not perms:
        return False

    ch = ctx.message.channel
    author = ctx.message.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


async def role_or_permissions(ctx, check, **perms):
    if await check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if isinstance(ch, discord.DMChannel):
        return False  # can't have roles in PMs

    role = discord.utils.find(check, author.roles)
    return role is not None


def role_or_mod_or_permissions(role=None, **perms):
    async def predicate(ctx):
        guild = ctx.guild
        mod_roles = [r.name.lower() for r in await ctx.bot.get_mod_roles(guild)]
        admin_roles = [r.name.lower() for r in await ctx.bot.get_admin_roles(guild)]
        roles = mod_roles + admin_roles
        if role:
            roles.append(role.lower())
        return await role_or_permissions(ctx, lambda r: r.name.lower() in roles, **perms)

    return commands.check(predicate)


def roles_or_mod_or_permissions(allowed_roles: dict = {}, **perms):
    async def predicate(ctx):
        guild = ctx.guild
        guild_roles = []
        if guild:
            server_roles = [
                discord.utils.get(ctx.guild.roles, id=int(r))
                for r in allowed_roles.get(guild.id, [])
            ]
            server_roles = [r.name.lower() for r in server_roles if r is not None]
        # TODO debug logging print(server_roles)
        mod_roles = [r.name.lower() for r in await ctx.bot.get_mod_roles(guild)]
        admin_roles = [r.name.lower() for r in await ctx.bot.get_admin_roles(guild)]
        roles = mod_roles + admin_roles + server_roles
        return await role_or_permissions(ctx, lambda r: r.name.lower() in roles, **perms)

    return commands.check(predicate)
