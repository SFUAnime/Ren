import discord

from redbot.core.commands import Context

from .core import AVATAR_FILE_NAME, Core, Modes


class CommandsCore(Core):
    async def cmdTriggered(self, ctx: Context, user: discord.User = None):
        """Are you triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.TRIGGERED)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))

    async def cmdHypertriggered(self, ctx: Context, user: discord.User = None):
        """Are you in an elevated state of triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.REALLY_TRIGGERED)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))

    async def cmdDeepfry(self, ctx: Context, user: discord.User = None):
        """Are you incredibly triggered? Say no more."""
        await ctx.defer()
        if not user:
            user = ctx.message.author
        data = await self._createTrigger(user, mode=Modes.HYPER_TRIGGERED)
        if not data:
            await ctx.send("Something went wrong, try again.")
            return
        await ctx.send(file=discord.File(data, filename=AVATAR_FILE_NAME.format(user)))
