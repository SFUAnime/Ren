from redbot.core.commands import Context

from .constants import KEY_ENABLED
from .core import Core


class CommandsCore(Core):
    async def cmdQrCheckerToggle(self, ctx: Context):
        """Toggle QR code checking"""
        guild = ctx.guild
        if not guild:
            return
        guildConfig = self.config.guild(guild)

        enabled: bool = await guildConfig.get_attr(KEY_ENABLED)()
        if enabled:
            await guildConfig.get_attr(KEY_ENABLED).set(False)
            await ctx.send("QR code checking is now **disabled** for this guild.")
        else:
            await guildConfig.get_attr(KEY_ENABLED).set(True)
            await ctx.send("QR code checking is now **enabled** for this guild.")
