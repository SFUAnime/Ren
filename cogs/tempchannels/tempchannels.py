"""Temporary channel cog.

Creates a temporary channel.
"""
from copy import deepcopy
from datetime import datetime
import logging
import time
import asyncio
import discord
from discord.ext import commands
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from .constants import *


class TempChannels(commands.Cog):
    """Creates a temporary channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.TempChannels")
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

        self.bgTask = self.bot.loop.create_task(self.checkChannels())

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.bgTask.cancel()

    async def _syncSettings(self):
        """Force settings to file and reload."""
        await self.config.put(KEY_SETTINGS, self.settings)
        self.settings = self.config.get(KEY_SETTINGS)

    @commands.group(name="tempchannels", aliases=["tc"])
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def tempChannels(self, ctx: Context):
        """Temporary text-channel creation (only 1 at the moment)."""

    @tempChannels.command(name="show")
    async def tempChannelsShow(self, ctx: Context):
        """Show current settings."""
        tempCh = await self.config.guild(ctx.guild).all()
        rolesAllow = [discord.utils.get(ctx.guild.roles, id=rid) for rid in tempCh[KEY_ROLE_ALLOW]]
        rolesAllow = [roleName.name for roleName in rolesAllow if roleName]
        rolesDeny = [discord.utils.get(ctx.guild.roles, id=rid) for rid in tempCh[KEY_ROLE_DENY]]
        rolesDeny = [roleName.name for roleName in rolesDeny if roleName]
        categoryName = discord.utils.get(ctx.guild.channels, id=tempCh[KEY_CH_CATEGORY])
        msg = (
            ":information_source: TempChannel - Current Settings\n```"
            "Enabled?       {}\n"
            "Archive after? {}\n"
            "NSFW Prompt:   {}\n"
            "Roles Allowed: {}\n"
            "Roles Denied:  {}\n"
            "Ch. Name:      #{}\n"
            "Ch. Topic:     {}\n"
            "Ch. Position:  {}\n"
            "Ch. Category:  {}\n"
            "Creation Time: {:002d}:{:002d}\n"
            "Duration:      {}h {}m"
            "```".format(
                "Yes" if tempCh[KEY_ENABLED] else "No",
                "Yes" if tempCh[KEY_ARCHIVE] else "No",
                "Yes" if tempCh[KEY_NSFW] else "No",
                rolesAllow,
                rolesDeny,
                tempCh[KEY_CH_NAME],
                tempCh[KEY_CH_TOPIC],
                tempCh[KEY_CH_POS],
                "{}".format(categoryName) if categoryName else "(not set)",
                tempCh[KEY_START_HOUR],
                tempCh[KEY_START_MIN],
                tempCh[KEY_DURATION_HOURS],
                tempCh[KEY_DURATION_MINS],
            )
        )

        await ctx.send(msg)

    @tempChannels.command(name="archive")
    @checks.admin()
    async def tempChannelsArchive(self, ctx: Context):
        """Toggle archiving the channel after the fact."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_ARCHIVE]:
                guildData[KEY_ARCHIVE] = False
                self.logger.info(
                    "%s (%s) DISABLED archiving the temp channel for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel: Archiving disabled. "
                    " The channel will be deleted after its lifetime expires."
                )
            else:
                guildData[KEY_ARCHIVE] = True
                self.logger.info(
                    "%s (%s) ENABLED archiving the temp channel for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":white_check_mark: TempChannel: Archiving enabled. The channel "
                    "will have ALL user permissions revoked after its lifetime "
                    "expires, and will be renamed with the date and time that it "
                    "was archived."
                )

    @tempChannels.command(name="toggle")
    async def tempChannelsToggle(self, ctx: Context):
        """Toggle the creation/deletion of the temporary channel."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_ENABLED]:
                guildData[KEY_ENABLED] = False
                self.logger.info(
                    "%s (%s) DISABLED the temp channel for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(":negative_squared_cross_mark: TempChannel: Disabled.")
            else:
                guildData[KEY_ENABLED] = True
                self.logger.info(
                    "%s (%s) ENABLED the temp channel for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(":white_check_mark: TempChannel: Enabled.")

    @tempChannels.command(name="nsfw")
    async def tempChannelsNSFW(self, ctx: Context):
        """Toggle NSFW requirements."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_NSFW]:
                nsfw = False
                self.logger.info(
                    "%s (%s) DISABLED the NSFW prompt for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.author.id,
                )
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel: NSFW " "requirement disabled."
                )
            else:
                guildData[KEY_NSFW] = True
                self.logger.info(
                    "%s (%s) ENABLED the NSFW prompt for %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(":white_check_mark: TempChannel: NSFW " "requirement enabled.")

    @tempChannels.command(name="start")
    async def tempChannelsStart(self, ctx: Context, hour: int, minute: int):
        """Set the temp channel creation time. Use 24 hour time.

        Parameters:
        -----------
        hour: int
            The hour to start the temporary channel.
        minute: int
            The minute to start the temporary channel.
        """
        if (hour > 23) or (hour < 0):
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Start "
                "Time: Please enter a valid time."
            )
            return
        if (minute > 59) or (minute < 0):
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Start "
                "Time: Please enter a valid time."
            )
            return

        async with self.config.guild(ctx.guild).all() as guildData:
            guildData[KEY_START_HOUR] = hour
            guildData[KEY_START_MIN] = minute
        self.logger.info(
            "%s (%s) set the start time to %002d:%002d on %s (%s)",
            ctx.author.name,
            ctx.author.id,
            hour,
            minute,
            ctx.guild.name,
            ctx.guild.id,
        )
        await ctx.send(
            ":white_check_mark: TempChannel - Start Time: Start time "
            "set to {0:002d}:{1:002d}.".format(hour, minute)
        )

    @tempChannels.command(name="duration")
    async def tempChannelsDuration(self, ctx: Context, hours: int, minutes: int):
        """Set the duration of the temp channel.  Max 100 hours.

        Parameters:
        -----------
        hours: int
            Number of hours to make this channel available.
        minutes: int
            Number of minutes to make this channel available.

        Example:
        If hours = 1, and minutes = 3, then the channel will be available for
        1 hour 3 minutes.
        """
        if (hours >= 100) or (hours < 0):
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Duration: "
                "Please enter valid hours!"
            )
            return
        if (minutes >= 60) or (minutes < 0):
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Duration: "
                "Please enter valid minutes!"
            )
            return
        if (hours >= 99) and (minutes >= 60):
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Duration: "
                "Please enter a valid duration!"
            )
            return

        async with self.config.guild(ctx.guild).all() as guildData:
            guildData[KEY_DURATION_HOURS] = hours
            guildData[KEY_DURATION_MINS] = minutes
        self.logger.info(
            "%s (%s) set the duration to %s hours, %s minutes on %s (%s)",
            ctx.author.name,
            ctx.author.id,
            hours,
            minutes,
            ctx.guild.name,
            ctx.guild.id,
        )

        await ctx.send(
            ":white_check_mark: TempChannel - Duration: Duration set to "
            "**{0} hours, {1} minutes**.".format(hours, minutes)
        )

    @tempChannels.command(name="topic")
    async def tempChannelsTopic(self, ctx: Context, *, topic: str):
        """Set the topic of the channel.

        Parameters:
        -----------
        topic: str
            The topic of the channel.
        """
        if len(topic) > MAX_CH_TOPIC:
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Topic: "
                "Topic is too long.  Try again."
            )
            return

        await self.config.guild(ctx.guild).channelTopic.set(topic)

        self.logger.info(
            "%s (%s) set the channel topic to the following on %s (%s): %s",
            ctx.author.name,
            ctx.author.id,
            ctx.guild.name,
            ctx.guild.id,
            topic,
        )

        await ctx.send(
            ":white_check_mark: TempChannel - Topic: Topic set to:\n" "```{0}```".format(topic)
        )

    @tempChannels.command(name="name")
    async def tempChannelsName(self, ctx, name: str):
        """Set the #name of the channel.

        Parameters:
        -----------
        name: str
            The #name of the channel, which is shown on the left panel of Discord.
        """
        if len(name) > MAX_CH_NAME:
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Name: "
                "Name is too long.  Try again."
            )
            return

        await self.config.guild(ctx.guild).channelName.set(name)

        self.logger.info(
            "%s (%s) set the channel name to " "%s" " on %s (%s)",
            ctx.author.name,
            ctx.author.id,
            name,
            ctx.guild.name,
            ctx.guild.id,
        )

        await ctx.send(
            ":white_check_mark: TempChannel - Name: Channel name set " "to: ``{0}``".format(name)
        )

    @tempChannels.command(name="position", aliases=["pos"])
    async def tempChannelsPosition(self, ctx, position: int):
        """Set the position of the text channel in the list.

        Parameters:
        -----------
        position: int
            The position where you want the temp channel to appear on the channel
            list.
        """
        if position > MAX_CH_POS or position < 0:
            await ctx.send(
                ":negative_squared_cross_mark: TempChannel - Position: "
                "Invalid position.  Try again."
            )
            return

        await self.config.guild(ctx.guild).channelPosition.set(position)
        self.logger.info(
            "%s (%s) changed the position to %s on %s (%s)",
            ctx.author.name,
            ctx.author.id,
            position,
            ctx.guild.name,
            ctx.guild.id,
        )

        await ctx.send(
            ":white_check_mark: TempChannel - Position: This channel "
            "will be at position {0}".format(position)
        )

    @tempChannels.command(name="category", pass_context=True, no_pm=True)
    async def tempChannelsCategory(
        self, ctx: Context, *, category: discord.CategoryChannel = None
    ):
        """Set the parent category of the text channel.

        Parameters:
        -----------
        category: discord.CategoryChannel
            The category you wish to nest the temporary channel under.
        """
        await self.config.guild(ctx.guild).channelCategory.set(category.id)

        if not category:
            self.logger.info(
                "%s (%s) disabled category nesting on %s (%s)",
                ctx.author.name,
                ctx.author.id,
                ctx.guild.name,
                ctx.guild.id,
            )
            await ctx.send(
                ":white_check_mark: TempChannel - Category: Parent " "category disabled."
            )
        else:
            self.logger.info(
                "%s (%s) set the parent category ID to %s on %s (%s)",
                ctx.author.name,
                ctx.author.id,
                category.id,
                ctx.guild.name,
                ctx.guild.id,
            )
            await ctx.send(
                ":white_check_mark: TempChannel - Category: Parent "
                "category set to **{}**.".format(category.name)
            )

    @tempChannels.command(name="allowadd", aliases=["aa"])
    async def tempChannelsAllowAdd(self, ctx: Context, *, role: discord.Role):
        """Add a role to allow access to the channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to allow access to the temporary channel.
        """
        async with self.config.guild(ctx.guild).roleAllow() as roleAllow:
            if role.id not in roleAllow:
                roleAllow.append(role.id)
                self.logger.info(
                    "%s (%s) added role %s to the allow list on %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    role.name,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":white_check_mark: TempChannel - Role Allow: **`{0}`"
                    "** will be allowed access.".format(role.name)
                )
            else:
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel - Role Allow: "
                    "**`{0}`** is already allowed.".format(role.name)
                )

    @tempChannels.command(name="allowremove", aliases=["allowdelete", "ad", "ar"])
    async def tempChannelsAllowRemove(self, ctx: Context, *, role: discord.Role):
        """Remove a role from being able access the temporary channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to remove access from.
        """
        async with self.config.guild(ctx.guild).roleAllow() as roleAllow:
            if not roleAllow or role.id not in roleAllow:
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel - Role Allow: "
                    "**`{0}`** wasn't on the list.".format(role.name)
                )
            else:
                roleAllow.remove(role.id)
                self.logger.info(
                    "%s (%s) removed role %s from the allow list on %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    role.name,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":white_check_mark: TempChannel - Role Allow: **`{0}`** "
                    "removed from the list.".format(role.name)
                )

    @tempChannels.command(name="denyadd", aliases=["da"])
    async def tempChannelsDenyAdd(self, ctx: Context, *, role: discord.Role):
        """Add a role to block sending message to the channel.

        This role should be HIGHER in the role hierarchy than the roles in
        the allowed list!  The bot will not check for this.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to deny sending permissions in the temporary channel.
        """
        async with self.config.guild(ctx.guild).roleDeny() as roleDeny:
            if role.id not in roleDeny:
                roleDeny.append(role.id)
                self.logger.info(
                    "%s (%s) added role %s to the deny list on %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    role.name,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":white_check_mark: TempChannel - Role: **`{0}`** will "
                    "be denied sending, provided this role is higher "
                    "than any of the ones in the allowed list.".format(role.name)
                )
            else:
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel - Role Deny: "
                    "**`{0}`** is already denied.".format(role)
                )

    @tempChannels.command(name="denyremove", aliases=["denydelete", "dd", "dr"])
    async def tempChannelsDenyRemove(self, ctx: Context, *, role: discord.Role):
        """Remove role from being blocked sending to the channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to remove from the deny list.
        """
        async with self.config.guild(ctx.guild).roleDeny() as roleDeny:
            if not roleDeny or role.id not in roleDeny:
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel - Role Deny: "
                    "**`{0}`** wasn't on the list.".format(role.name)
                )
            else:
                roleDeny.remove(role.id)
                self.logger.info(
                    "%s (%s) removed role %s from the deny list on %s (%s)",
                    ctx.author.name,
                    ctx.author.id,
                    role.name,
                    ctx.guild.name,
                    ctx.guild.id,
                )
                await ctx.send(
                    ":white_check_mark: TempChannel - Role Deny: **`{0}`** "
                    "removed from the list.".format(role.name)
                )

    @tempChannels.command(name="delete", aliases=["remove", "del", "rm"])
    async def tempChannelsDelete(self, ctx: Context):
        """Deletes the temp channel, if it exists."""
        async with self.config.guild(ctx.guild).all() as guildData:
            if guildData[KEY_CH_CREATED] and guildData[KEY_CH_ID]:
                # Channel created, see when we should delete it.
                try:
                    chanObj = self.bot.get_channel(guildData[KEY_CH_ID])
                    await chanObj.delete()
                except discord.DiscordException:
                    self.logger.error("Could not delete channel!", exc_info=True)
                    await ctx.send(
                        ":warning: TempChannel: Something went wrong "
                        "while trying to delete the channel. Please "
                        "check the console log for details."
                    )
                else:
                    guildData[KEY_CH_ID] = None
                    guildData[KEY_CH_CREATED] = False
                    self.logger.info(
                        "%s (%s) deleted the temp channel #%s (%s) in %s (%s).",
                        ctx.author.name,
                        ctx.author.id,
                        chanObj.name,
                        chanObj.id,
                        ctx.guild.name,
                        ctx.guild.id,
                    )
                    await ctx.send(":white_check_mark: TempChannel: Channel deleted")
            else:
                await ctx.send(
                    ":negative_squared_cross_mark: TempChannel: There is no "
                    "temporary channel to delete!"
                )

    ###################
    # Background Loop #
    ###################
    async def checkChannels(self):  # pylint: disable=too-many-branches,too-many-statements
        """Loop to check whether or not we should create/delete the
        TempChannel."""
        while self == self.bot.get_cog("TempChannels"):
            await asyncio.sleep(SLEEP_TIME)
            # Create/maintain the channel during a valid time and duration, else
            # delete it.
            for guild in self.bot.guilds:
                async with self.config.guild(guild).all() as guildData:
                    try:
                        if not guildData[KEY_ENABLED]:
                            continue

                        if (
                            int(time.strftime("%H")) == guildData[KEY_START_HOUR]
                            and int(time.strftime("%M")) == guildData[KEY_START_MIN]
                            and not guildData[KEY_CH_CREATED]
                            and not guildData[KEY_CH_ID]
                        ):
                            # See if ALL of the following is satisfied.
                            # - It is the starting time.
                            # - The channel creation flag is not set.
                            # - The channel ID doesn't exist.
                            #
                            # If it is satisfied, let's create a channel, and then
                            # store the following in the settings:
                            # - Channel ID.
                            # - Time to delete channel.
                            # Start with permissions

                            # Always allow the bot to read.
                            permsDict = {self.bot.user: PERMS_READ_Y}

                            if guildData[KEY_ROLE_ALLOW]:
                                # If we have allow roles, automatically deny @everyone the "Read
                                # Messages" permission.
                                permsDict[guild.default_role] = PERMS_READ_N
                                for roleId in guildData[KEY_ROLE_ALLOW]:
                                    role = discord.utils.get(guild.roles, id=roleId)
                                    self.logger.debug("Allowed role %s", role)
                                    if role:
                                        permsDict[role] = deepcopy(PERMS_READ_Y)

                            # Check for deny permissions.
                            if guildData[KEY_ROLE_DENY]:
                                for roleId in guildData[KEY_ROLE_DENY]:
                                    role = discord.utils.get(guild.roles, id=roleId)
                                    self.logger.debug("Denied role %s", role)
                                    if role and role not in permsDict.keys():
                                        self.logger.debug("Role not in dict, adding")
                                        permsDict[role] = deepcopy(PERMS_SEND_N)
                                    elif role:
                                        self.logger.debug("Updating role")
                                        permsDict[role].update(send_messages=False)

                            self.logger.debug("Current permission overrides: \n%s", permsDict)

                            # Grab parent category. If not set, this will return None anyways.
                            category = None
                            if guildData[KEY_CH_CATEGORY]:
                                category = discord.utils.get(
                                    guild.channels, id=guildData[KEY_CH_CATEGORY]
                                )

                            chanObj = await guild.create_text_channel(
                                guildData[KEY_CH_NAME],
                                overwrites=permsDict,
                                category=category,
                                position=guildData[KEY_CH_POS],
                                topic=guildData[KEY_CH_TOPIC],
                                nsfw=guildData[KEY_NSFW],
                            )
                            self.logger.info(
                                "Channel #%s (%s) in %s (%s) was created.",
                                chanObj.name,
                                chanObj.id,
                                guild.name,
                                guild.id,
                            )
                            guildData[KEY_CH_ID] = chanObj.id

                            # Set delete times, and save settings.
                            duration = (
                                guildData[KEY_DURATION_HOURS] * 60 * 60
                                + guildData[KEY_DURATION_MINS] * 60
                            )
                            guildData[KEY_STOP_TIME] = time.time() + duration
                            guildData[KEY_CH_CREATED] = True

                        elif guildData[KEY_CH_CREATED]:
                            # Channel created, see when we should delete it.
                            if time.time() >= guildData[KEY_STOP_TIME]:
                                self.logger.debug(
                                    "Past channel stop time, clearing ID " "and created keys."
                                )
                                chanObj = guild.get_channel(guildData[KEY_CH_ID])
                                guildData[KEY_CH_ID] = None
                                guildData[KEY_CH_CREATED] = False

                                if chanObj and guildData[KEY_ARCHIVE]:
                                    await chanObj.set_permissions(
                                        guild.default_role, overwrite=PERMS_READ_N
                                    )
                                    for role in guild.roles:
                                        if role == guild.default_role:
                                            continue
                                        await chanObj.set_permissions(
                                            role, overwrite=None, reason="Archiving tempchannel"
                                        )
                                    currentDate = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                                    await chanObj.edit(name=f"tc-{currentDate}")
                                    self.logger.info(
                                        "Channel #%s (%s) in %s (%s) was archived.",
                                        chanObj.name,
                                        chanObj.id,
                                        guild.name,
                                        guild.id,
                                    )
                                elif chanObj and not guildData[KEY_ARCHIVE]:
                                    await chanObj.delete()

                                    self.logger.info(
                                        "Channel #%s (%s) in %s (%s) was deleted.",
                                        chanObj.name,
                                        chanObj.id,
                                        guild.name,
                                        guild.id,
                                    )
                    except Exception:  # pylint: disable=broad-except
                        self.logger.error(
                            "Something went terribly wrong for server %s (%s)!",
                            guild.name,
                            guild.id,
                            exc_info=True,
                        )
