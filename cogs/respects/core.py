import logging
import os
from asyncio import Lock
from datetime import datetime, timedelta
from random import choice
import discord
from discord.errors import NotFound, HTTPException
import discord.utils
from redbot.core import Config, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import humanize_list

from .constants import *


class Core:
    def __init__(self, bot: Red):
        self.bot = bot
        self.plusFLock = Lock()
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)
        self.config.register_channel(**BASE_CHANNEL)

        # Initialize logger and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Respects")
        if not self.logger.handlers:
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%Y/%m/%d %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    async def checkLastRespect(self, ctx: Context):
        """Check to see if respects have been paid already.

        This method only checks the time portion, previous messages
        and the last respect.

        Returns:
        --------
        This method returns `False` if:
        - No respects have been paid in the channel before, or
        - The last respect could not be retrieved, or
        - The current respect is paid to a message that is different from
          the message to which the last respect was paid, or
        - The time exceeds the threshold AND the last respect in the channel was behind
          more than a certain number of messages.

        Otherwise, this method returns `True`.
        """

        chConfig = self.config.channel(ctx.channel)
        guildConfig = self.config.guild(ctx.guild)

        oldRespectMsgId = await chConfig.get_attr(KEY_MSG)()

        if not oldRespectMsgId:
            return False
        else:
            oldRespect = None
            try:
                oldRespect = await ctx.channel.fetch_message(oldRespectMsgId)
            except (NotFound, HTTPException) as e:
                # in any of these cases, we assume the old respect is lost
                # and past data should be cleared
                await chConfig.clear()
                if isinstance(e, NotFound):
                    self.logger.debug("Could not find the old respect")
                else:
                    self.logger.error("Could not retrieve the old respect", exc_info=True)
                return False
            else:
                oldReference = None
                if oldRespect:
                    oldReference = oldRespect.reference

                currentRespect = ctx.message
                currentReference = currentRespect.reference

                if currentReference:
                    if not oldReference or oldReference.message_id != currentReference.message_id:
                        self.logger.debug(
                            "Two most recent respects were paid to two different messages"
                        )
                        self.logger.debug("Resetting the respect chain")
                        await chConfig.clear()
                        return False

        confMsgsBetween = await guildConfig.get_attr(KEY_MSGS_BETWEEN)()
        confTimeBetween = await guildConfig.get_attr(KEY_TIME_BETWEEN)()
        oldRespectTime = await chConfig.get_attr(KEY_TIME)()

        prevMsgIds = []

        async for msg in ctx.channel.history(
            limit=confMsgsBetween,
            before=ctx.message,
        ):
            prevMsgIds.append(msg.id)

        exceedMessages = oldRespectMsgId not in prevMsgIds
        exceedTime = datetime.now() - datetime.fromtimestamp(oldRespectTime) > timedelta(
            seconds=confTimeBetween
        )

        self.logger.debug(
            "Messages between: %s, Time between: %s",
            confMsgsBetween,
            confTimeBetween,
        )
        self.logger.debug("Last respect time: %s", datetime.fromtimestamp(oldRespectTime))
        self.logger.debug("exceedMessages: %s, exceedTime: %s", exceedMessages, exceedTime)

        if exceedMessages and exceedTime:
            self.logger.debug("We've exceeded the messages/time between respects")
            await chConfig.clear()
            return False

        return True

    async def checkIfUserPaidRespect(self, ctx):
        """Check to see if the user has already paid their respects.

        This assumes that `checkLastRespectTime` returned True.
        """

        paidRespectsUsers = await self.config.channel(ctx.channel).get_attr(KEY_USERS)()
        if ctx.author.id in paidRespectsUsers:
            self.logger.debug("The user has already paid their respects")
            return True
        return False

    async def payRespects(self, ctx: Context):
        """Pay respects.

        This assumes that `checkLastRespectTime` has been invoked.

        """
        async with self.config.channel(ctx.channel).all() as chData:
            chData[KEY_USERS].append(ctx.author.id)
            chData[KEY_TIME] = datetime.now().timestamp()

            oldReference = None

            if chData[KEY_MSG]:
                try:
                    oldRespect = await ctx.channel.fetch_message(chData[KEY_MSG])
                    oldReference = oldRespect.reference if oldRespect else None
                    await oldRespect.delete()
                except NotFound:
                    self.logger.debug("Could not find the old respect")
                except HTTPException:
                    self.logger.error("Could not retrieve the old respect", exc_info=True)
                finally:
                    chData[KEY_MSG] = None

            confUserIds = chData[KEY_USERS]
            currentGuild: discord.Guild = ctx.guild
            members = list(
                filter(
                    lambda member: member,
                    (currentGuild.get_member(uid) for uid in reversed(confUserIds)),
                )
            )

            message = "{memberNames} {haveHas} paid their respects {heartEmote}".format(
                memberNames=humanize_list([member.mention for member in members]),
                haveHas=("has" if len(members) == 1 else "have"),
                heartEmote=choice(HEARTS),
            )

            newReference = ctx.message.reference if ctx.message.reference else oldReference
            if newReference:
                newReference.fail_if_not_exists = False

            messageEmbed = discord.Embed(description=message)
            messageEmbed.set_footer(text=f"Use {ctx.clean_prefix}f to pay respects")

            messageObj = await ctx.send(
                embed=messageEmbed,
                reference=newReference,
                mention_author=False,
            )
            chData[KEY_MSG] = messageObj.id
