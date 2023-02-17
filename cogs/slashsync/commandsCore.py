from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import info, success

from .core import Core


class CommandsCore(Core):
    async def cmdSync(self, ctx: Context):
        msg = await ctx.send(info("Syncing slash commands to Discord, please wait..."))
        await self.bot.tree.sync()
        await msg.edit(content=success("Synchronized slash commands to Discord."))
