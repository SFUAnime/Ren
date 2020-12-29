"""Respects cog
A replica of +f seen in another bot, except smarter..
"""
import logging
from datetime import datetime, timedelta
from threading import Lock
from random import choice
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

KEY_USERS = "users"
KEY_TIME = "time"
KEY_MSG = "msg"
KEY_TIME_BETWEEN = "timeSinceLastRespect"
KEY_MSGS_BETWEEN = "msgsSinceLastRespect"
HEARTS = [
    ":green_heart:",
    ":heart:",
    ":black_heart:",
    ":yellow_heart:",
    ":purple_heart:",
    ":blue_heart:",
]
DEFAULT_TIME_BETWEEN = timedelta(seconds=30)  # Time between paid respects.
DEFAULT_MSGS_BETWEEN = 20  # The number of messages in between
TEXT_RESPECTS = "paid their respects"

BASE_GUILD = {KEY_TIME_BETWEEN: 30, KEY_MSGS_BETWEEN: 20}
BASE_CHANNEL = {KEY_MSG: None, KEY_TIME: None, KEY_USERS: []}


class Respects(commands.Cog):
    """Pay your respects."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.plusFLock = Lock()
        self.settingsLock = Lock()
        self.settings = {}
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)
        self.config.register_channel(**BASE_CHANNEL)

        # Initialize logger and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Respects")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename=str(saveFolder) + "/info.log", encoding="utf-8", mode="a"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    @commands.command(name="f")
    @commands.guild_only()
    async def plusF(self, ctx: Context):
        """Pay your respects."""
        with self.plusFLock:
            if not await self.checkLastRespect(ctx):
                # New respects to be paid
                await self.payRespects(ctx)
            elif not await self.checkIfUserPaidRespect(ctx):
                # Respects exists, user has not paid their respects yet.
                await self.payRespects(ctx)
            else:
                # Respects already paid by user!
                pass
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                await ctx.send(
                    "I currently cannot delete messages. Please give me the"
                    ' "Manage Messages" permission to allow this feature to'
                    " work!"
                )

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="setf")
    @commands.guild_only()
    async def setf(self, ctx: Context):
        """Respect settings."""

    @setf.command(name="messages", aliases=["msgs"])
    @commands.guild_only()
    async def setfMessages(self, ctx: Context, messages: int):
        """Set the number of messages that must appear before a new respect is paid.

        Parameters:
        -----------
        messages: int
            The number of messages between messages.  Should be between 1 and 100
        """
        if messages < 1 or messages > 100:
            await ctx.send(
                ":negative_squared_cross_mark: Please enter a number " "between 1 and 100!"
            )
            return

        await self.config.guild(ctx.message.guild).msgsSinceLastRespect.set(messages)
        timeBetween = await self.config.guild(ctx.message.guild).timeSinceLastRespect()
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

    @setf.command(name="show")
    @commands.guild_only()
    async def setfShow(self, ctx: Context):
        """Show the current settings."""
        guild = ctx.message.guild
        timeBetween = await self.config.guild(guild).timeSinceLastRespect()
        msgsBetween = await self.config.guild(guild).msgsSinceLastRespect()

        msg = ":information_source: **Respects - Current Settings:**\n"
        msg += "A new respect will be made if a previous respect does not exist, or:\n"
        msg += "- **{}** messages have been passed since the last respect, **and**\n"
        msg += "- **{}** seconds have passed since the last respect."
        await ctx.send(msg.format(msgsBetween, timeBetween))

    @setf.command(name="time", aliases=["seconds"])
    @commands.guild_only()
    async def setfTime(self, ctx, seconds: int):
        """Set the number of seconds that must pass before a new respect is paid.

        Parameters:
        -----------
        seconds: int
            The number of seconds that must pass.  Should be between 1 and 100
        """
        if seconds < 1 or seconds > 100:
            await ctx.send(
                ":negative_squared_cross_mark: Please enter a number " "between 1 and 100!"
            )
            return

        await self.config.guild(ctx.guild).timeSinceLastRespect.set(seconds)
        messagesBetween = await self.config.guild(ctx.guild).msgsSinceLastRespect()
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

    async def checkLastRespect(self, ctx):
        """Check to see if respects have been paid already.

        This method only checks the time portion and previous messages.

        This method returns False if:
        - No respects have been paid in this channel before, or
        - The time exceeds the threshold AND the last respect in the channel was more
          than a certain number of messages.

        Otherwise, this method returns True.
        """
        chData = await self.config.channel(ctx.channel).all()
        guildData = await self.config.guild(ctx.guild).all()

        if not chData[KEY_MSG]:
            return False

        prevMsgs = []

        async for msg in ctx.channel.history(
            limit=guildData[KEY_MSGS_BETWEEN], before=ctx.message
        ):
            prevMsgs.append(msg.id)

        exceedMessages = chData[KEY_MSG] not in prevMsgs
        exceedTime = datetime.now() - datetime.fromtimestamp(chData[KEY_TIME]) > timedelta(
            seconds=guildData[KEY_TIME_BETWEEN]
        )

        self.logger.debug(
            "Messages between: %s, Time between: %s",
            guildData[KEY_MSGS_BETWEEN],
            guildData[KEY_TIME_BETWEEN],
        )
        self.logger.debug("Last respect time: %s", datetime.fromtimestamp(chData[KEY_TIME]))
        self.logger.debug("exceedMessages: %s, exceedTime: %s", exceedMessages, exceedTime)

        if exceedMessages and exceedTime:
            self.logger.debug("We've exceeded the messages/time between respects")
            await self.config.channel(ctx.channel).clear()
            return False

        return True

    async def checkIfUserPaidRespect(self, ctx):
        """Check to see if the user has already paid their respects.

        This assumes that checkLastRespectTime returned True.
        """
        paidRespectsUsers = await self.config.channel(ctx.channel).users()
        if ctx.author.id in paidRespectsUsers:
            self.logger.debug("The user has already paid their respects")
            return True
        return False

    async def payRespects(self, ctx: Context):
        """Pay respects.

        This assumes that checkLastRespectTime has been invoked.

        """
        async with self.config.channel(ctx.channel).all() as chData:
            chData[KEY_USERS].append(ctx.author.id)
            chData[KEY_TIME] = datetime.now().timestamp()

            if chData[KEY_MSG]:
                try:
                    oldRespect = await ctx.channel.fetch_message(chData[KEY_MSG])
                    await oldRespect.delete()
                except (discord.Forbidden, discord.NotFound):
                    await ctx.send(
                        'I currently cannot delete messages, please give me "Manage'
                        ' Message" permissions to allow this feature to work!'
                    )
                finally:
                    chData[KEY_MSG] = None

            if len(chData[KEY_USERS]) == 1:
                message = "**{}** has paid their respects {}".format(
                    ctx.author.name, choice(HEARTS)
                )
            elif len(chData[KEY_USERS]) == 2:  # 2 users, no comma.
                user1 = ctx.author
                uid2 = chData[KEY_USERS][0]
                user2 = discord.utils.get(ctx.guild.members, id=uid2)
                users = "**{} and {}**".format(user1.name, user2.name)
                message = "{} have paid their respects {}".format(users, choice(HEARTS))
            else:
                first = True
                users = ""
                for userId in chData[KEY_USERS]:
                    userObj = discord.utils.get(ctx.guild.members, id=userId)
                    if first:
                        users = "and {}".format(userObj.name)
                        first = False
                    else:
                        users = "{}, {}".format(userObj.name, users)
                message = "**{}** have paid their respects {}".format(users, choice(HEARTS))

            messageObj = await ctx.send(message)
            chData[KEY_MSG] = messageObj.id
