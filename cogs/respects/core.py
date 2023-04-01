import os
from asyncio import Lock
from datetime import datetime, timedelta
from logging import FileHandler, Formatter, Logger, getLogger
from pathlib import Path
from random import choice
from typing import List, Optional
from discord import Embed, Guild, Member, Message, MessageReference
from discord.errors import NotFound, HTTPException
from redbot.core import Config, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.config import Group
from redbot.core.utils.chat_formatting import humanize_list

from .constants import *


class Core:
    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.plusFLock: Lock = Lock()
        self.config: Config = Config.get_conf(
            self,
            identifier=5842647,
            force_registration=True,
        )
        self.config.register_guild(**BASE_GUILD)
        self.config.register_channel(**BASE_CHANNEL)

        # Initialize logger and save to cog folder.
        saveFolder: Path = data_manager.cog_data_path(cog_instance=self)
        self.logger: Logger = getLogger("red.luicogs.Respects")
        if not self.logger.handlers:
            logPath: str = os.path.join(saveFolder, "info.log")
            handler: FileHandler = FileHandler(
                filename=logPath,
                encoding="utf-8",
                mode="a",
            )
            handler.setFormatter(
                Formatter("%(asctime)s %(message)s", datefmt="[%Y/%m/%d %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    async def checkLastRespect(self, ctx: Context) -> bool:
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

        chConfig: Group = self.config.channel(ctx.channel)
        guildConfig: Group = self.config.guild(ctx.guild)

        oldRespectMsgId: Optional[int] = await chConfig.get_attr(KEY_MSG)()

        if not oldRespectMsgId:
            return False
        else:
            oldRespect: Optional[Message] = None
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
                oldReference: Optional[MessageReference] = None
                if oldRespect:
                    oldReference = oldRespect.reference

                currentRespect: Message = ctx.message
                currentReference: Optional[MessageReference] = currentRespect.reference

                if currentReference:
                    if not oldReference or oldReference.message_id != currentReference.message_id:
                        self.logger.debug(
                            "Two most recent respects were paid to two different messages"
                        )
                        self.logger.debug("Resetting the respect chain")
                        await chConfig.clear()
                        return False

        confMsgsBetween: int = await guildConfig.get_attr(KEY_MSGS_BETWEEN)()
        confTimeBetween: float = await guildConfig.get_attr(KEY_TIME_BETWEEN)()
        oldRespectTime: float = await chConfig.get_attr(KEY_TIME)()

        prevMsgIds: List[int] = []

        async for msg in ctx.channel.history(
            limit=confMsgsBetween,
            before=ctx.message,
        ):
            prevMsgIds.append(msg.id)

        exceedMessages: bool = oldRespectMsgId not in prevMsgIds
        exceedTime: bool = datetime.now() - datetime.fromtimestamp(oldRespectTime) > timedelta(
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

    async def checkIfUserPaidRespect(self, ctx: Context) -> bool:
        """Check to see if the user has already paid their respects.

        This assumes that `checkLastRespectTime` returned True.
        """

        paidRespectsUsers: List[int] = await self.config.channel(ctx.channel).get_attr(KEY_USERS)()
        if ctx.author.id in paidRespectsUsers:
            self.logger.debug("The user has already paid their respects")
            return True
        return False

    async def payRespects(self, ctx: Context) -> None:
        """Pay respects.

        This assumes that `checkLastRespectTime` has been invoked.

        """
        async with self.config.channel(ctx.channel).all() as chData:
            chData[KEY_USERS].append(ctx.author.id)
            chData[KEY_TIME] = datetime.now().timestamp()

            oldReference: Optional[MessageReference] = None

            if chData[KEY_MSG]:
                try:
                    oldRespect: Message = await ctx.channel.fetch_message(chData[KEY_MSG])
                    oldReference = oldRespect.reference if oldRespect else None
                    await oldRespect.delete()
                except NotFound:
                    self.logger.debug("Could not find the old respect")
                except HTTPException:
                    self.logger.error("Could not retrieve the old respect", exc_info=True)
                finally:
                    chData[KEY_MSG] = None

            confUserIds: List[int] = chData[KEY_USERS]
            currentGuild: Guild = ctx.guild
            members: List[Member] = list(
                filter(
                    lambda member: member,
                    (currentGuild.get_member(uid) for uid in reversed(confUserIds)),
                )
            )

            message: str = "{memberNames} {haveHas} paid their respects {heartEmote}".format(
                memberNames=humanize_list([member.mention for member in members]),
                haveHas=("has" if len(members) == 1 else "have"),
                heartEmote=choice(HEARTS),
            )

            newReference: Optional[MessageReference] = (
                ctx.message.reference if ctx.message.reference else oldReference
            )
            if newReference:
                newReference.fail_if_not_exists = False

            messageEmbed: Embed = Embed(description=message)
            messageEmbed.set_footer(text=f"Use {ctx.clean_prefix}f to pay respects")

            messageObj: Message = await ctx.send(
                embed=messageEmbed,
                reference=newReference,
                mention_author=False,
            )
            chData[KEY_MSG] = messageObj.id
