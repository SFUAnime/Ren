from discord.errors import NotFound, HTTPException
from redbot.core.commands.context import Context
from redbot.core.config import Group

from .constants import KEY_MSGS_BETWEEN, KEY_TIME_BETWEEN
from .core import Core


class CommandsCore(Core):
    async def cmdPlusF(self, ctx: Context) -> None:
        """Pay your respects."""

        async with self.plusFLock:
            if not await self.checkLastRespect(ctx):
                # New respects to be paid
                await self.payRespects(ctx)
            elif not await self.checkIfUserPaidRespect(ctx):
                # Respects exists, user has not paid their respects yet.
                await self.payRespects(ctx)
            elif ctx.interaction is not None:
                await ctx.send("You have already paid your respects!", ephemeral=True)
                return

        try:
            await ctx.message.delete()
        except NotFound:
            self.logger.debug("Could not find the old respect")
        except HTTPException:
            self.logger.error("Could not retrieve the old respect", exc_info=True)

    async def cmdSetFMessages(self, ctx: Context, messages: int) -> None:
        """Set the number of messages that must appear before a new respect is paid.

        Parameters:
        -----------
        messages: int
            The number of messages between messages.  Should be between 1 and 100
        """

        if messages < 1 or messages > 100:
            await ctx.send(
                ":negative_squared_cross_mark: Please enter a number between 1 and 100!"
            )
            return

        guildConfig: Group = self.config.guild(ctx.guild)

        await guildConfig.get_attr(KEY_MSGS_BETWEEN).set(messages)
        timeBetween: float = await guildConfig.get_attr(KEY_TIME_BETWEEN)()

        await ctx.send(
            ":white_check_mark: **Respects - Messages**: A new respect will be "
            "created after **{}** messages and **{}** seconds have passed "
            "since the previous one.".format(messages, timeBetween)
        )

        self.logger.info(
            "%s#%s (%s) changed the messages between respects to %s messages",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            messages,
        )

    async def cmdSetFShow(self, ctx: Context) -> None:
        """Show the current settings."""

        guildConfig: Group = self.config.guild(ctx.guild)

        timeBetween: float = await guildConfig.get_attr(KEY_TIME_BETWEEN)()
        msgsBetween: int = await guildConfig.get_attr(KEY_MSGS_BETWEEN)()

        msg: str = ":information_source: **Respects - Current Settings:**\n"
        msg += "A new respect will be made if a previous respect does not exist, or:\n"
        msg += "- **{}** messages have been passed since the last respect, **and**\n"
        msg += "- **{}** seconds have passed since the last respect."
        await ctx.send(msg.format(msgsBetween, timeBetween))

    async def cmdSetFTime(self, ctx: Context, seconds: int) -> None:
        """Set the number of seconds that must pass before a new respect is paid.

        Parameters:
        -----------
        seconds: int
            The number of seconds that must pass.  Should be between 1 and 100
        """
        if seconds < 1 or seconds > 100:
            await ctx.send(
                ":negative_squared_cross_mark: Please enter a number between 1 and 100!"
            )
            return

        guildConfig: Group = self.config.guild(ctx.guild)

        await guildConfig.get_attr(KEY_TIME_BETWEEN).set(seconds)
        messagesBetween: int = await guildConfig.get_attr(KEY_MSGS_BETWEEN)()

        await ctx.send(
            ":white_check_mark: **Respects - Time**: A new respect will be "
            "created after **{}** messages and **{}** seconds have passed "
            "since the previous one.".format(messagesBetween, seconds)
        )

        self.logger.info(
            "%s#%s (%s) changed the time between respects to %s seconds",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            seconds,
        )
