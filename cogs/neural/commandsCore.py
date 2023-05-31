from redbot.core.commands import Context

from .constants import KEY_NEURAL_ACTIVE
from .core import Core


class CommandsCore(Core):
    async def commandNeuralActivate(self, ctx: Context) -> None:
        """Activate the neural cog for the current channel."""
        await self.initChannelChatState(ctx.channel)
        await self.config.channel(ctx.channel).get_attr(KEY_NEURAL_ACTIVE).set(True)
        await ctx.send("SYSTEM: The neural cog is now **activated** for this channel.")

    async def commandNeuralDeactivate(self, ctx: Context) -> None:
        """Deactivate the neural cog for the current channel."""
        await self.config.channel(ctx.channel).get_attr(KEY_NEURAL_ACTIVE).set(False)
        await ctx.send("SYSTEM: The neural cog is now **deactivated** for this channel.")
