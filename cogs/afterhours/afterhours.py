"""After hours module.

A special cog to handle the special cases for this channel.
"""
import os
import re
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils.chat_formatting import humanize_timedelta

# Basic constants
AH_CHANNEL = "after-hours"
KEY_CTX_CHANNEL_ID = "channelId"
KEY_CHANNEL_IDS = "channelIds"
KEY_ROLE_ID = "roleId"
STARBOARD = "highlights"
DELETE_TIME = 32 * 60 * 60
SLEEP_TIME = 60 * 60

# Logging
KEY_LAST_MSG_TIMESTAMPS = "lastMsgTimestamps"

# Auto-purging
KEY_AUTO_PURGE = "autoPurge"
KEY_BACKGROUND_LOOP = "backgroundLoop"
KEY_INACTIVE_DURATION = "inactiveDuration"  # unit of time: seconds

# Default guild settings
DEFAULT_GUILD = {
    KEY_CTX_CHANNEL_ID: None,
    KEY_CHANNEL_IDS: {},
    KEY_ROLE_ID: None,
    KEY_LAST_MSG_TIMESTAMPS: {},
    KEY_AUTO_PURGE: {
        KEY_BACKGROUND_LOOP: True,
        KEY_INACTIVE_DURATION: 0,
    },
}


class AfterHours(commands.Cog):
    """Special casing galore!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.AfterHours")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)
        self.bgTask = self.bot.loop.create_task(self.backgroundLoop())

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.logger.info("Unloading cog")
        self.bgTask.cancel()

    def cog_unload(self):
        self.logger.info("Unloading cog")
        self.__unload()

    async def backgroundLoop(self):
        """Background loop to garbage collect and purge"""
        while True:
            self.logger.debug("Checking to see if we need to garbage collect")
            await self.checkGarbageCollect()

            self.logger.debug("Executing auto-purge")
            await self.doAutoPurge()

            await asyncio.sleep(SLEEP_TIME)

    async def checkGarbageCollect(self):
        for guild in self.bot.guilds:
            self.logger.debug("Checking guild %s", guild.id)
            async with self.config.guild(guild).get_attr(KEY_CHANNEL_IDS)() as channels:
                staleIds = []
                for channelId, data in channels.items():
                    self.logger.debug("Checking channel ID %s", channelId)
                    channel = discord.utils.get(guild.channels, id=int(channelId))
                    if not channel:
                        self.logger.error("Channel ID %s doesn't exist!", channelId)
                        staleIds.append(channelId)
                        continue
                    creationTime = datetime.fromtimestamp(data["time"])
                    self.logger.debug("Time difference = %s", datetime.now() - creationTime)
                    if datetime.now() - creationTime > timedelta(seconds=DELETE_TIME):
                        self.logger.info("Deleting channel %s (%s)", channel.name, channel.id)
                        await channel.delete(reason="AfterHours purge")
                        # Don't delete the ID here, this will be taken care of in
                        # the delete listener
                for channelId in staleIds:
                    self.logger.info("Purging stale channel ID %s", channelId)
                    del channels[channelId]

    async def doAutoPurge(self, forced=False):
        for guild in self.bot.guilds:
            guildConfig = self.config.guild(guild)
            autoPurgeConfig = guildConfig.get_attr(KEY_AUTO_PURGE)
            autoPurgeInactiveDurationConfig = autoPurgeConfig.get_attr(KEY_INACTIVE_DURATION)

            if not forced and await autoPurgeConfig.get_attr(KEY_BACKGROUND_LOOP)() is False:
                self.logger.debug(
                    "Background execution of auto-purged is disabled for guild %s", guild.id
                )
                continue

            # skip this guild if there is no AfterHours role
            ahRoleId: int = await guildConfig.get_attr(KEY_ROLE_ID)()
            if not ahRoleId:
                self.logger.debug("No AfterHours role ID set for guild %s", guild.id)
                continue
            else:
                ahRole: discord.Role = discord.utils.get(guild.roles, id=int(ahRoleId))
                if not ahRole:
                    self.logger.debug("AfterHours role does not exist in guild %s!", guild.id)
                    continue

            # a list of members to be purged
            inactiveMembers: List[discord.Member] = []

            # check for inactive members based on a set inactive duration
            inactiveDuration: int = await autoPurgeInactiveDurationConfig()

            inactiveDurationTimeDelta = timedelta(seconds=inactiveDuration)

            if not inactiveDurationTimeDelta or inactiveDurationTimeDelta < timedelta(seconds=1):
                self.logger.debug(
                    "Auto-purge based on inactive duration is not enabled for guild %s", guild.id
                )
                continue

            self.logger.debug(
                "Auto-purge based on inactive duration is enabled for guild %s (inactive duration %s)",
                guild.id,
                inactiveDurationTimeDelta,
            )

            async with guildConfig.get_attr(KEY_LAST_MSG_TIMESTAMPS)() as lastMsgTimestamps:
                for member in ahRole.members:
                    if not member.bot:
                        memberId = str(member.id)
                        if memberId in lastMsgTimestamps:
                            lastMsgTime = datetime.fromtimestamp(lastMsgTimestamps[memberId])
                            if datetime.utcnow() - lastMsgTime > inactiveDurationTimeDelta:
                                inactiveMembers.append(member)
                        else:
                            self.logger.debug(
                                "User %s has no AfterHours message timestamp recorded, "
                                "therefore assuming the last message timestamp is right now",
                                memberId,
                            )
                            lastMsgTimestamps[memberId] = int(datetime.utcnow().timestamp())

            # purge inactive members
            try:
                async with guildConfig.get_attr(KEY_LAST_MSG_TIMESTAMPS)() as lastMsgTimestamps:
                    for inactiveMember in inactiveMembers:
                        # obtain information
                        memberName = inactiveMember.name
                        memberDiscriminator = inactiveMember.discriminator
                        memberId = str(inactiveMember.id)
                        # purge this inactive member
                        await inactiveMember.remove_roles(ahRole, reason="AfterHours auto-purge")
                        self.logger.info(
                            "Removed role %s from %s#%s (%s) due to inactivity",
                            ahRole.name,
                            memberName,
                            memberDiscriminator,
                            memberId,
                        )
                        # clean up dict entry for this member
                        del lastMsgTimestamps[memberId]
            except discord.Forbidden:
                self.logger.error(
                    "Auto-purge failed due to missing permissions for guild %s", guild.id
                )
            except discord.HTTPException:
                self.logger.error(
                    "Auto-purge failed due to HTTP error for guild %s", guild.id, exc_info=True
                )

    async def getContext(self, channel: discord.TextChannel):
        """Get the Context object from a text channel.

        Parameters
        ----------
        channel: discord.TextChannel
            The text channel to use in order to create the Context object.

        Returns
        -------
        ctx: Context
            The context needed to send messages and invoke methods from other cogs.
        """
        ctxGuild = channel.guild
        ctxChannelId = await self.config.guild(ctxGuild).get_attr(KEY_CTX_CHANNEL_ID)()
        ctxChannel = discord.utils.get(ctxGuild.channels, id=ctxChannelId)
        if not ctxChannel:
            self.logger.error("Cannot find channel to construct context!")
            return None
        async for message in ctxChannel.history(limit=1):
            lastMessage = message
        return await self.bot.get_context(lastMessage)

    async def makeStarboardChanges(
        self, ctx: Context, channel: discord.abc.GuildChannel, remove=False
    ):
        """Apply Starboard changes.

        Parameters
        -----------
        ctx: Context
            The Context object in order to invoke commands
        channel: discord.abc.GuildChannel
            The channel to apply Starboard changes to.
        remove: bool
            Indicate whether we want to remove the changes. Defaults to False.
        """
        self.logger.info("Applying/removing Starboard exceptions, remove=%s", remove)
        sbCog = self.bot.get_cog("Starboard")
        if not sbCog:
            self.logger.error("Starboard not loaded. skipping")
            return

        try:
            starboard = sbCog.starboards[ctx.guild.id]["highlights"]
        except KeyError:
            self.logger.error("Cannot get the starboard!")
        else:
            if remove:
                await ctx.invoke(
                    sbCog.blacklist_remove, starboard=starboard, channel_or_role=channel
                )
            else:
                await ctx.invoke(sbCog.blacklist_add, starboard=starboard, channel_or_role=channel)

    async def notifyChannel(self, ctx, remove=False):
        if remove:
            await ctx.send(f":information_source: **{AH_CHANNEL} removed, removing exceptions**")
        else:
            await ctx.send(f":information_source: **{AH_CHANNEL} created, adding exceptions**")

    async def makeWordFilterChanges(
        self, ctx: Context, channel: discord.abc.GuildChannel, remove=False
    ):
        """Apply WordFilter changes.

        Parameters
        -----------
        ctx: Context
            The Context object in order to invoke commands
        channel: discord.abc.GuildChannel
            The channel to apply WordFilter changes to.
        remove: bool
            Indicate whether we want to remove the changes. Defaults to False.
        """
        self.logger.info("Applying/removing WordFilter exceptions, remove=%s", remove)
        cog = self.bot.get_cog("WordFilter")
        if not cog:
            self.logger.error("WordFilter not loaded. skipping")
            return

        if remove:
            await ctx.invoke(cog._channelRemove, channel=channel)
        else:
            await ctx.invoke(cog._channelAdd, channel=channel)

    @commands.Cog.listener("on_guild_channel_create")
    async def handleChannelCreate(self, channel: discord.abc.GuildChannel):
        """Listener to see if we need to add exceptions to a channel"""
        self.logger.info(
            "Channel creation has been detected. Name: %s, ID: %s", channel.name, channel.id
        )

        if not isinstance(channel, discord.TextChannel):
            return

        if channel.name == AH_CHANNEL:
            self.logger.info("%s detected, applying exceptions", AH_CHANNEL)
            ctx = await self.getContext(channel)
            if not ctx:
                return
            await self.notifyChannel(ctx)
            await self.makeStarboardChanges(ctx, channel)
            await self.makeWordFilterChanges(ctx, channel)
            async with self.config.guild(channel.guild).get_attr(KEY_CHANNEL_IDS)() as channelIds:
                channelIds[channel.id] = {"time": datetime.now().timestamp()}

    @commands.Cog.listener("on_guild_channel_delete")
    async def handleChannelDelete(self, channel: discord.abc.GuildChannel):
        """Listener to see if we need to remove exceptions from a channel"""
        self.logger.info(
            "Channel deletion has been detected. Name: %s, ID: %s", channel.name, channel.id
        )

        if not isinstance(channel, discord.TextChannel):
            return

        async with self.config.guild(channel.guild).get_attr(KEY_CHANNEL_IDS)() as channelIds:
            if str(channel.id) in channelIds:
                self.logger.info("%s detected, removing exceptions", AH_CHANNEL)
                ctx = await self.getContext(channel)
                if not ctx:
                    return
                await self.notifyChannel(ctx, remove=True)
                await self.makeStarboardChanges(ctx, channel, remove=True)
                await self.makeWordFilterChanges(ctx, channel, remove=True)
                del channelIds[str(channel.id)]

    async def saveMessageTimestamp(self, message: discord.Message, timestamp: float):
        guildConfig = self.config.guild(message.guild)

        async with guildConfig.get_attr(KEY_CHANNEL_IDS)() as channels:
            if str(message.channel.id) not in channels:
                return

            async with guildConfig.get_attr(KEY_LAST_MSG_TIMESTAMPS)() as lastMsgTimestamps:
                lastMsgTimestamps[message.author.id] = timestamp

    @commands.Cog.listener("on_message")
    async def handleMessage(self, message: discord.Message):
        """Listener to save every AfterHours member's latest message's timestamp for purging purposes"""
        # Ignore on DMs.
        if not isinstance(message.channel, discord.TextChannel):
            return

        # ignore bot messages
        if message.author.bot:
            return

        await self.saveMessageTimestamp(message, message.created_at.timestamp())

    @commands.Cog.listener("on_message_edit")
    async def handleMessageEdit(self, before: discord.Message, after: discord.Message):
        """Listener to save every AfterHours member's latest message's timestamp for purging purposes"""
        # Ignore on DMs.
        if not isinstance(after.channel, discord.TextChannel):
            return

        # ignore bot messages
        if after.author.bot:
            return

        if after.edited_at:
            await self.saveMessageTimestamp(after, after.edited_at.timestamp())

    @commands.group(name="afterhours")
    @commands.guild_only()
    async def afterHours(self, ctx: Context):
        """Manage after-hours"""

    @checks.mod_or_permissions(manage_messages=True)
    @afterHours.command(name="setrole")
    async def afterHoursSetRole(self, ctx: Context, role: discord.Role):
        """Set the after-hours role.

        This allows for self-removals later.

        Parameters
        ----------
        role: discord.Role
            The role associated with after hours.
        """
        await self.config.guild(ctx.guild).get_attr(KEY_ROLE_ID).set(role.id)
        await ctx.send(f"Set the After Hours role to {role.name}")

    @afterHours.command(name="removerole")
    async def afterHoursRemoveRole(self, ctx: Context):
        """Remove the after-hours role from yourself."""
        # check if after hours role is set
        roleid = await self.config.guild(ctx.guild).get_attr(KEY_ROLE_ID)()
        if roleid is None:
            await ctx.send("Please configure the after-hours role first!")
            return
        # get after hours role by id
        role = ctx.guild.get_role(roleid)
        # if id is no longer valid (role deleted most likely)
        if role is None:
            await ctx.send(
                "After Hours role no longer valid, most likely role was deleted by admins"
            )
            return

        # check if user has roles
        rolesList = ctx.author.roles
        if role not in rolesList:
            await ctx.send(f"You do not have the role {role.name}")
            return
        # remove role
        try:
            await ctx.author.remove_roles(role, reason="User removed role")
        except discord.Forbidden:
            self.logger.error("Not allowed to remove role", exc_info=True)
        except discord.HTTPException:
            self.logger.error("HTTP Exception", exc_info=True)

        # post message saying role removed
        await ctx.send(f"Removed the role {role.name} from you.")

    @checks.mod_or_permissions(manage_messages=True)
    @afterHours.command(name="setchannel")
    async def afterHoursSet(self, ctx: Context):
        """Set the channel for notifications."""
        await self.config.guild(ctx.guild).get_attr(KEY_CTX_CHANNEL_ID).set(ctx.channel.id)
        await ctx.send("Using this channel to construct context later!")

    @checks.mod()
    @afterHours.group(name="autopurge")
    async def afterHoursAutoPurge(self, ctx: Context):
        """Manage auto-purge

        Auto-purge is by default executed at the same frequency as the AfterHours background loop.
        Refer to the subcommands section to see the subcommand to disable this behavior.
        """

    @checks.mod()
    @checks.bot_has_permissions(manage_roles=True)
    @afterHoursAutoPurge.command(name="now")
    async def afterHoursAutoPurgeNow(self, ctx: Context):
        """Execute auto-purge immediately"""
        await ctx.send("Purging...")
        await self.doAutoPurge(forced=True)
        await ctx.send("Purge completed!")

    @checks.admin()
    @afterHoursAutoPurge.command(name="togglebackground")
    async def afterHoursAutoPurgeToggleBackgroundLoop(self, ctx: Context):
        """Toggle auto-purge background loop
        If it is disabled, the AfterHours background loop will not execute auto-purge.
        """
        guildConfig = self.config.guild(ctx.guild)
        autoPurgeConfig = guildConfig.get_attr(KEY_AUTO_PURGE)
        bgLoopConfig = autoPurgeConfig.get_attr(KEY_BACKGROUND_LOOP)
        if await bgLoopConfig() is True:
            await bgLoopConfig.set(False)
            await ctx.send("Disabled auto-purge background loop")
        else:
            await bgLoopConfig.set(True)
            await ctx.send("Enabled auto-purge background loop")

    @checks.admin()
    @afterHoursAutoPurge.command(name="inactiveduration")
    async def afterHoursAutoPurgeInactiveDuration(self, ctx: Context, *, duration: Optional[str]):
        """View or set the duration of inactivity for auto-purge.

        Parameters
        ----------
        duration: str
            The duration string, containing none, some or all of the following non-negative numbers (max. 5 digits), optionally separated by spaces, **in order**:
            - Number of years (365-day equivalent), optionally followed by spaces, followed by `y`/`yr[s]`/`year[s]`.
            - Number of months (30-day equivalent), optionally followed by spaces, followed by `mo[s]`/`month[s]`.
            - Number of weeks, optionally followed by spaces, followed by `w`/`wk[s]`/`week[s]`.
            - Number of days, optionally followed by spaces, followed by `d`/`day[s]`.
            - Number of hours, optionally followed by spaces, followed by `h`/`hr[s]`/`hour[s]`.
            - Number of minutes, optionally followed by spaces, followed by `m`/`min[s]`/`minute[s]`.
            - Number of seconds, optionally followed by spaces, followed by `s`/`sec[s]`/`second[s]`.
            Set this to 0 or a duration equivalent to 0 to disable auto-purging based on inactive duration.
            Leave blank to check the current settings.
        """

        guildConfig = self.config.guild(ctx.guild)
        autoPurgeConfig = guildConfig.get_attr(KEY_AUTO_PURGE)
        autoPurgeInactiveDurationConfig = autoPurgeConfig.get_attr(KEY_INACTIVE_DURATION)

        if duration:
            if duration == "0":
                await autoPurgeInactiveDurationConfig.set(0)
                await ctx.send("Disabled auto-purge on inactive duration.")
                return
            else:
                match = re.match(
                    r"^\s*"
                    r"(?:(\d{1,5})\s*y(?:(?:ea)?rs?)?)?"  # years
                    r"\s*"
                    r"(?:(\d{1,5})\s*mo(?:nth)?s?)?"  # months
                    r"\s*"
                    r"(?:(\d{1,5})\s*w(?:(?:ee)?ks?)?)?"  # weeks
                    r"\s*"
                    r"(?:(\d{1,5})\s*d(?:ays?)?)?"  # days
                    r"\s*"
                    r"(?:(\d{1,5})\s*h(?:(?:ou)?rs?)?)?"  # hours
                    r"\s*"
                    r"(?:(\d{1,5})\s*m(?:in(?:ute)?s?)?)?"  # minutes
                    r"\s*"
                    r"(?:(\d{1,5})\s*s(?:ec(?:ond)?s?)?)?"  # seconds
                    r"\s*$",
                    duration,
                    re.IGNORECASE,
                )
                if match is None:
                    await ctx.send("Invalid duration.")
                    return
                else:
                    groups = match.groups()
                    years, months, weeks, days, hours, minutes, seconds = [
                        int(x) if x else 0 for x in groups
                    ]

                    totalSeconds = (
                        years * 365 * 24 * 60 * 60
                        + months * 30 * 24 * 60 * 60
                        + weeks * 7 * 24 * 60 * 60
                        + days * 24 * 60 * 60
                        + hours * 60 * 60
                        + minutes * 60
                        + seconds
                    )

                    await autoPurgeInactiveDurationConfig.set(totalSeconds)

                    if totalSeconds == 0:
                        await ctx.send("Disabled auto-purge on inactive duration.")
                    else:
                        await ctx.send(
                            f"Set the inactive duration for auto-purge to {humanize_timedelta(seconds=totalSeconds)}."
                        )
        else:
            totalSeconds: int = await autoPurgeInactiveDurationConfig()
            if totalSeconds == 0:
                await ctx.send("The inactive duration for auto-purge is currently not set.")
            else:
                await ctx.send(
                    f"The inactive duration for auto-purge is currently set to {humanize_timedelta(seconds=totalSeconds)}."
                )
