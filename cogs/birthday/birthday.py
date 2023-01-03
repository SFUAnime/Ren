"""Birthday cog Automatically add users to a specified birthday role on their
birthday."""
import logging
import os
from random import choice
import time  # To auto remove birthday role on the next day.
import asyncio
from datetime import date, datetime, timedelta
import discord
from typing import Union
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands.context import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.chat_formatting import bold, pagify, spoiler, warning
from redbot.core.bot import Red
from .constants import *
from .converters import MonthDayConverter


class Birthday(commands.Cog):
    """Adds a role to someone on their birthday, and automatically remove them
    from this role after the day is over."""

    def initializeConfigAndLogger(self):
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        # Register default (empty) settings.
        self.config.register_guild(**BASE_GUILD)
        self.config.register_member(**BASE_GUILD_MEMBER)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Birthday")
        if not self.logger.handlers:
            logPath = os.path.join(saveFolder, "info.log")
            handler = logging.FileHandler(filename=logPath, encoding="utf-8", mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    def initializeBgTask(self):
        # On cog load, we want the loop to run once.
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.birthdayLoop())

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.bgTask: asyncio.Task = None
        self.config: Config = None
        self.lastChecked: datetime = None
        self.logger: logging.Logger = None

        self.initializeConfigAndLogger()
        self.initializeBgTask()

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()

    @commands.group(name="birthday")
    @commands.guild_only()
    async def _birthday(self, ctx: Context):
        """Birthday role assignment settings."""

    @_birthday.command(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setChannel(self, ctx: Context, channel: discord.TextChannel = None):
        """Set the channel to mention members on their birthday.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            A text channel to mention a member's birthday.
        """

        if channel:
            await self.config.guild(ctx.guild).get_attr(KEY_BDAY_CHANNEL).set(channel.id)
            self.logger.info(
                "%s#%s (%s) set the birthday channel to %s",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                channel.name,
            )
            await ctx.send(
                ":white_check_mark: **Birthday - Channel**: **{}** has been set "
                "as the birthday mention channel!".format(channel.name)
            )
        else:
            await self.config.guild(ctx.guild).get_attr(KEY_BDAY_CHANNEL).set(None)
            await ctx.send(
                ":white_check_mark: **Birthday - Channel**: Birthday mentions are now disabled."
            )

    @_birthday.command(name="role")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setRole(self, ctx: Context, role: discord.Role):
        """Set the role to assign to a birthday user. Make sure this role can
        be assigned and removed by the bot by placing it in the correct
        hierarchy location.

        Parameters:
        -----------
        role: discord.Role
            A role (name or mention) to set as the birthday role.
        """

        await self.config.guild(ctx.guild).get_attr(KEY_BDAY_ROLE).set(role.id)
        self.logger.info(
            "%s#%s (%s) set the birthday role to %s",
            ctx.author.name,
            ctx.author.discriminator,
            ctx.author.id,
            role.name,
        )
        await ctx.send(
            ":white_check_mark: **Birthday - Role**: **{}** has been set "
            "as the birthday role!".format(role.name)
        )

    @_birthday.command(name="test")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def test(self, ctx: Context):
        """Test at-mentions."""
        for msg in CANNED_MESSAGES:
            await ctx.send(msg.format(ctx.author.mention))

    @_birthday.command(name="add", aliases=["set"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def addMemberBirthday(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        birthday: MonthDayConverter = None,
    ):
        """Add a user's birthday to the list.

        If the birthday is not specified, it defaults to today.
        On the day, the bot will automatically add the user to the birthday role.

        Parameters:
        -----------
        member: discord.Member
            The member whose birthday is being assigned.

        birthday: (optional)
            The user's birthday, with the year omitted. If entering only numbers, specify the month first.
            For example: Feb 29, February 29, 2/29.
        """
        rid = await self.config.guild(ctx.guild).get_attr(KEY_BDAY_ROLE)()

        # Check if guild is initialized.
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Add**: "
                "This server is not configured, please set a role!"
            )
            return

        if not birthday:
            birthday = datetime.today()
        day = birthday.day
        month = birthday.month

        def check(msg: discord.Message):
            return msg.author == ctx.author and msg.channel == ctx.channel

        async with self.config.member(member).all() as userConfig:
            addedBefore = userConfig[KEY_ADDED_BEFORE]
            birthdayExists = userConfig[KEY_BDAY_MONTH] and userConfig[KEY_BDAY_DAY]
            if not birthdayExists and addedBefore:
                await ctx.send(
                    warning(
                        f"This user had their birthday previously removed. Are you sure you "
                        "still want to re-add them? Please type `yes` to confirm."
                    )
                )
                try:
                    response = await self.bot.wait_for("message", timeout=30.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f"You took too long, not re-adding them.")
                    return

                if response.content.lower() != "yes":
                    await ctx.send(f"Not re-adding them to the birthday list.")
                    return

            userConfig[KEY_BDAY_MONTH] = month
            userConfig[KEY_BDAY_DAY] = day

        confMsg = await ctx.send(
            ":white_check_mark: **Birthday - Add**: Successfully {0} **{1}**'s birthday "
            "as **{2:%B} {2:%d}**. The role will be assigned automatically on this "
            "day.".format("updated" if birthdayExists else "added", member.name, birthday)
        )

        # Explicitly check to see if user should be added to role, if the month
        # and day just so happen to be the same as it is now.
        await self.checkBirthday()

        await asyncio.sleep(5)  # pylint: disable=no-member

        await confMsg.edit(
            content=":white_check_mark: **Birthday - Add**: Successfully {0} **{1}**'s "
            "birthday, and the role will be automatically assigned on the day.".format(
                "updated" if birthdayExists else "added", member.name
            )
        )

        self.logger.info(
            "%s#%s (%s) added the birthday of %s#%s (%s) as %s",
            ctx.author.name,
            ctx.author.discriminator,
            ctx.author.id,
            member.name,
            member.discriminator,
            member.id,
            birthday.strftime("%B %d"),
        )
        return

    @_birthday.command(name="list", aliases=["ls"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def listBirthdays(self, ctx: Context):
        """Lists the birthdays of users in the server."""

        sortedList = []  # List to sort by month, day.
        display = []  # List of text for paginator to use.  Will be constructed from sortedList.

        # Add only the users we care about (e.g. the ones that have birthdays set).
        membersData = await self.config.all_members(ctx.guild)
        for memberId, memberDetails in membersData.items():
            # Check if the birthdate keys exist, and they are not null.
            # If true, add an ID key and append to list.
            if (
                KEY_BDAY_DAY in memberDetails.keys()
                and KEY_BDAY_MONTH in memberDetails.keys()
                and memberDetails[KEY_BDAY_DAY]
                and memberDetails[KEY_BDAY_MONTH]
            ):
                memberDetails["ID"] = memberId
                sortedList.append(memberDetails)

        # Check if any birthdays have been set before sorting
        if not sortedList:
            await ctx.send(
                ":warning: **Birthday - List**: There are no birthdates "
                "set on this server. Please add some first!"
            )
            return

        # Sort by month, day.
        sortedList.sort(key=lambda x: (x[KEY_BDAY_MONTH], x[KEY_BDAY_DAY]))

        for user in sortedList:
            # Get the associated user Discord object.
            userObject = discord.utils.get(ctx.guild.members, id=user["ID"])

            # Skip if user is no longer in server.
            if not userObject:
                continue

            # The year below is just there to accommodate leap year.  Not used anywhere else.
            userBirthday = datetime(2020, user[KEY_BDAY_MONTH], user[KEY_BDAY_DAY])
            text = "{0:%B} {0:%d}: {1}".format(userBirthday, userObject.name)
            display.append(text)

        pageList = []
        msg = "\n".join(display)
        pages = list(pagify(msg, page_length=300))
        totalPages = len(pages)
        async for pageNumber, page in AsyncIter(pages).enumerate(start=1):
            embed = discord.Embed(title=f"Birthdays in **{ctx.guild.name}**", description=page)
            embed.set_footer(text=f"Page {pageNumber}/{totalPages}")
            embed.colour = discord.Colour.red()
            pageList.append(embed)
        await menu(ctx, pageList, DEFAULT_CONTROLS)

    @_birthday.command(name="unassign")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def unassignRole(self, ctx: Context, member: discord.Member):
        """Unassign the birthday role from a user.

        Parameters:
        -----------
        member: discord.Member
            The guild member that you want to remove the birthday role from.
        """
        rid = await self.config.guild(ctx.guild).get_attr(KEY_BDAY_ROLE)()
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Unassign**: This "
                "server is not configured, please set a role!"
            )
            return

        try:
            # Find the Role object to remove from the member.
            role = discord.utils.get(ctx.guild.roles, id=rid)

            # Remove role from the user.
            await member.remove_roles(role)
        except discord.Forbidden:
            self.logger.error(
                "Could not unassign %s#%s (%s) from the birthday role, does "
                "the bot have enough permissions?",
                member.name,
                member.discriminator,
                member.id,
                exc_info=True,
            )
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Unassign**: "
                "Could not unassign **{}** from the role, the bot does not "
                "have enough permissions to do so! Please make sure that "
                "the bot is above the birthday role, and that it has the "
                "Manage Roles permission!".format(member.name)
            )
            return

        await self.config.member(member).get_attr(KEY_IS_ASSIGNED).set(False)

        await ctx.send(
            ":white_check_mark: **Birthday - Unassign**: Successfully "
            "unassigned **{}** from the birthday role.".format(member.name)
        )

        self.logger.info(
            "%s#%s (%s) unassigned %s#%s (%s) from the birthday role",
            ctx.author.name,
            ctx.author.discriminator,
            ctx.author.id,
            member.name,
            member.discriminator,
            member.id,
        )
        return

    @_birthday.command(name="delete", aliases=["del", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def deleteMemberBirthday(self, ctx: Context, member: discord.Member):
        """Delete a user's birthday role and birthday from the list.

        Parameters:
        -----------
        member: discord.Member
            The guild member whose birthday role and saved birthday you want to remove.
        """
        rid = await self.config.guild(ctx.guild).get_attr(KEY_BDAY_ROLE)()
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Delete**: This "
                "server is not configured, please set a role!"
            )
            return

        try:
            # Find the Role object to remove from the member.
            role = discord.utils.get(ctx.guild.roles, id=rid)

            # Remove role from the user.
            await member.remove_roles(role)
        except discord.Forbidden:
            self.logger.error(
                "Could not remove %s#%s (%s) from the birthday role, does "
                "the bot have enough permissions?",
                member.name,
                member.discriminator,
                member.id,
                exc_info=True,
            )
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Delete**: "
                "Could not remove **{}** from the role, the bot does not "
                "have enough permissions to do so! Please make sure that "
                "the bot is above the birthday role, and that it has the "
                "Manage Roles permission!".format(member.name)
            )
            return

        async with self.config.member(member).all() as userConfig:
            userConfig[KEY_ADDED_BEFORE] = True
            userConfig[KEY_IS_ASSIGNED] = False
            userConfig[KEY_BDAY_MONTH] = None
            userConfig[KEY_BDAY_DAY] = None

        await ctx.send(
            ":white_check_mark: **Birthday - Delete**: Deleted birthday of **{}** ".format(
                member.name
            )
        )

        self.logger.info(
            "%s#%s (%s) deleted the birthday of %s#%s (%s)",
            ctx.author.name,
            ctx.author.discriminator,
            ctx.author.id,
            member.name,
            member.discriminator,
            member.id,
        )
        return

    @_birthday.group(name="self", aliases=["me"])
    @commands.guild_only()
    async def me(self, ctx: Context):
        """Manage your birthday."""
        # this method is not named "self" because it is a Python reserved keyword

    @me.command("get", aliases=["display", "show"])
    @commands.guild_only()
    async def getSelfBirthday(self, ctx: Context):
        """Display your birthday."""
        fnTitle = "Birthday - Get Self's Birthday"
        headerBad = f":negative_squared_cross_mark: {bold(fnTitle)}"
        headerGood = f":white_check_mark: {bold(fnTitle)}"
        headerWarn = warning(bold(fnTitle))
        noDmStr = "\n".join(
            (
                f"{headerWarn}: I would like to DM you your birthday but it seeems that "
                "you have disabled DMs from this server. Would you still like to continue here? "
                "Your birthday will be sent here and deleted after a short delay. ",
                f"Type {bold('`yes`', escape_formatting=False)} to confirm. ",
                "Anything else will be treated as no.",
            )
        )

        birthdayConfig = self.config.member(ctx.author)
        if birthdayConfig:
            details: typing.Dict = await birthdayConfig.all()
            if details:
                month: int = details.get(KEY_BDAY_MONTH)
                day: int = details.get(KEY_BDAY_DAY)
                if month and day:
                    birthday = date(2020, month, day)
                    birthdayStr = "{0:%B} {0:%d}".format(birthday)
                    birthdayInfoMsg = (
                        f"{headerGood}: Your birthday is "
                        f"{spoiler(bold(birthdayStr, escape_formatting=False), escape_formatting=False)}."
                    )
                    try:
                        await ctx.author.send(birthdayInfoMsg)
                        return
                    except discord.Forbidden:
                        await ctx.send(noDmStr)

                        def check(msg: discord.Message):
                            return msg.author == ctx.author and msg.channel == ctx.channel

                        try:
                            response = await self.bot.wait_for(
                                "message", timeout=30.0, check=check
                            )
                        except asyncio.TimeoutError:
                            await ctx.send(f"{headerBad}: No response detected. Aborting.")
                            return

                        if response.content.lower() != "yes":
                            await ctx.send(f"{headerBad}: Aborting.")
                            return
                        await ctx.send(birthdayInfoMsg, delete_after=5)
                        return
        setSelfBirthdayCmd: commands.Command = self.setSelfBirthday
        helpSetSelfBirthdayCmdStr = (
            # pylint: disable=no-member
            f"`{ctx.clean_prefix}help {setSelfBirthdayCmd.qualified_name}`"
            # pylint: enable=no-member
        )

        replyMsg = (
            f"{headerBad}: "
            "Your birthday in this server has not been set. "
            "Please contact an administrator/moderator, or, "
            "if it is allowed by the server's admins and/or "
            "moderators, try setting it yourself. Reference "
            f"{helpSetSelfBirthdayCmdStr} for the command syntax."
        )
        await ctx.send(replyMsg)

    @me.command("set", aliases=["add"])
    @commands.guild_only()
    async def setSelfBirthday(self, ctx: Context, *, birthday: MonthDayConverter):
        """Set your birthday.

        If this function is enabled, you can set your birthday ONCE, and ONLY IF your
        birthday were not already set. Otherwise, if not enabled, you need to contact an
        administrator or a moderator in case you want to have your birthday erased and/or set.

        For your privacy, you can delete the command message right away after sending it.

        Parameters
        ----------
        birthday:
            Your birthday, with the year omitted. If entering only numbers, specify the month first.
            For example: Feb 29, February 29, 2/29.
        """
        fnTitle = "Birthday - Set Self's Birthday"
        headerBad = f":negative_squared_cross_mark: {bold(fnTitle)}"
        headerGood = f":white_check_mark: {bold(fnTitle)}"
        headerWarn = warning(bold(fnTitle))

        if not await self.config.guild(ctx.guild).get_attr(KEY_ALLOW_SELF_BDAY)():
            await ctx.send(
                f"{headerBad}: "
                "This function is not enabled. You cannot set your birthday. "
                "Please let an administrator or a moderator know if you "
                "believe this function should be enabled."
            )
            return

        birthdayConfig = self.config.member(ctx.author)
        if birthdayConfig:
            birthMonth = birthdayConfig.get_attr(KEY_BDAY_MONTH)
            birthDay = birthdayConfig.get_attr(KEY_BDAY_DAY)
            if birthMonth and birthDay and await birthMonth() and await birthDay():
                await ctx.send(
                    f"{headerBad}: "
                    "Your birthday is already set. If you believe it is "
                    "incorrect, please contact an admin or a moderator."
                )
                return

        birthdayRoleId = await self.config.guild(ctx.guild).get_attr(KEY_BDAY_ROLE)()

        if not birthdayRoleId:
            await ctx.send(
                f"{headerBad}: "
                "This server is not configured, please let a server "
                "administrator or moderator know."
            )
            return

        birthdayStr = "{0:%B} {0:%d}".format(birthday)
        if birthdayConfig:

            async def mainFlow(channel: discord.TextChannel, carefree: bool = False):
                confirmationStr = "\n".join(
                    (
                        f"Are you sure you want to set your birthday to "
                        f"{spoiler(bold(birthdayStr, escape_formatting=False), escape_formatting=False)}? "
                        "Only administrators and moderators can reset your birthday afterwards.",
                        f"Type {bold('`yes`', escape_formatting=False)} to confirm.",
                    )
                )
                # define the time for sensitive messages to live for
                SENSITIVE_MSG_TTL = None if carefree else 5.0
                try:
                    await channel.send(
                        f"{headerWarn}: {confirmationStr}",
                        delete_after=SENSITIVE_MSG_TTL,
                    )
                except discord.Forbidden:
                    # this means messages cannot be sent to the the destination channel
                    # so we abort the flow now by re-raising the exception
                    # and the caller shall handle it gracefully
                    raise

                # wait for answer
                def check(msg: discord.Message):
                    return msg.author == ctx.author and msg.channel == channel

                # define response wait time
                responseTimeout = SENSITIVE_MSG_TTL + 1 if SENSITIVE_MSG_TTL else 30
                try:
                    response = await self.bot.wait_for("message", timeout=responseTimeout, check=check)
                except asyncio.TimeoutError:
                    await channel.send(
                        f"{headerBad}: You took too long. Not setting your birthday."
                    )
                    return

                if response.content.lower() != "yes":
                    await channel.send(f"{headerBad}: Declined. Not setting your birthday.")
                    return

                # Set birthday and notify user that their birthday has been set
                await birthdayConfig.get_attr(KEY_BDAY_MONTH).set(birthday.month)
                await birthdayConfig.get_attr(KEY_BDAY_DAY).set(birthday.day)
                await birthdayConfig.get_attr(KEY_ADDED_BEFORE).set(True)

                await channel.send(
                    f"{headerGood}: Successfully set your birthday to "
                    f"{spoiler(bold(birthdayStr, escape_formatting=False), escape_formatting=False)}.",
                    delete_after=SENSITIVE_MSG_TTL,
                )

                self.logger.info(
                    "%s#%s (%s) added their birthday as %s",
                    ctx.author.name,
                    ctx.author.discriminator,
                    ctx.author.id,
                    birthdayStr,
                )

                # explicitly check to see if the role should be applied to the user
                # if the month and day just so happen to be the same as it is now.
                await self.checkBirthday()
                return

            noDmStr = "\n".join(
                (
                    "You have disabled DMs from this server. Would you "
                    "still like to continue here? All messages containing your "
                    "birthday will be deleted after a short delay.",
                    f"Type {bold('`yes`', escape_formatting=False)} to confirm.",
                )
            )
            try:
                await mainFlow(ctx.author.dm_channel, carefree=True)
                return
            except discord.Forbidden:
                await ctx.send(noDmStr)

                def check(msg: discord.Message):
                    return msg.author == ctx.author and msg.channel == ctx.channel

                try:
                    response = await self.bot.wait_for("message", timeout=10.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f"{headerBad}: You took too long. Not setting your birthday.")
                    return

                if response.content.lower() != "yes":
                    await ctx.send(f"{headerBad}: Declined. Not setting your birthday.")
                    return
                await mainFlow(ctx.channel, carefree=False)

    @_birthday.command(name="selfbirthday")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def toggleSelfBirthday(self, ctx: Context):
        """Allow or disallow members to set their birthdays themselves.

        If allowed, members can set their birthdays themselves ONCE, and
        ONLY IF their birthdays were not already set. Otherwise, if not
        allowed, members need to contact an administrator or a moderator
        in case they want to have their birthdays erased and/or set.
        """
        fnTitle = "Birthday - Toggle Self Birthday"
        headerGood = f":white_check_mark: {bold(fnTitle)}"

        msgAllow = (
            f"{headerGood}: "
            f"{bold('Enabled')}. Members can set their birthdays themselves "
            f"{bold('ONCE')} and {bold('ONLY IF')} their birthdays were not already set."
        )
        msgNotAllow = (
            f"{headerGood}: {bold('Disabled')}. Members cannot set their birthdays themselves."
        )
        guildConfig = self.config.guild(ctx.guild)
        allowSelfBirthdayConfig = guildConfig.get_attr(KEY_ALLOW_SELF_BDAY)
        if await allowSelfBirthdayConfig():
            await allowSelfBirthdayConfig.set(False)
            await ctx.send(msgNotAllow)
        else:
            await allowSelfBirthdayConfig.set(True)
            await ctx.send(msgAllow)

    def getBirthdayMessage(self, member: discord.Member) -> str:
        """Get the birthday message.

        Parameters
        ----------
        member: discord.Member
            The member that we want the birthday message for.

        Returns
        -------
        str
            The birthday message, already formatted.
        """
        if self.bot.user.id == member.id:
            return BOT_BIRTHDAY_MSG
        return choice(CANNED_MESSAGES).format(member.mention)

    async def checkBirthday(self):
        """Check birthday list once."""
        await self._dailySweep()
        await self._dailyAdd()

    async def birthdayLoop(self):
        """The main event loop that will call the add and sweep methods."""
        self.logger.info("Waiting for bot to be ready")
        await self.bot.wait_until_red_ready()
        self.logger.info("Bot is ready")
        while self == self.bot.get_cog("Birthday"):
            if self.lastChecked.day != datetime.now().day:
                self.lastChecked = datetime.now()
                await self.checkBirthday()
            await asyncio.sleep(60)  # pylint: disable=no-member

    async def _dailySweep(self):
        """Check to see if any users should have the birthday role removed."""
        guilds = self.bot.guilds

        # Avoid having data modified by other methods.
        # When we acquire the lock for all members, it also prevents lock for guild
        # from being acquired, which is what we want.
        membersLock = self.config.get_members_lock()

        async with membersLock:
            # Check each guild.
            for guild in guilds:
                # Make sure the guild is configured with birthday role.
                # If it's not, skip over it.
                bdayRoleId = await self.config.guild(guild).get_attr(KEY_BDAY_ROLE)()
                if not bdayRoleId:
                    continue

                # Check to see if any users need to be removed.
                memberData = await self.config.all_members(guild)  # dict
                for memberId, memberDetails in memberData.items():
                    # If assigned and the date is different than the date assigned, remove role.
                    if memberDetails[KEY_IS_ASSIGNED] and memberDetails[KEY_BDAY_DAY] != int(
                        time.strftime("%d")
                    ):

                        role = discord.utils.get(guild.roles, id=bdayRoleId)
                        member = discord.utils.get(guild.members, id=memberId)

                        if member:
                            # Remove the role
                            try:
                                await member.remove_roles(role)
                                self.logger.info(
                                    "Removed birthday role from %s#%s (%s)",
                                    member.name,
                                    member.discriminator,
                                    member.id,
                                )
                            except discord.Forbidden:
                                self.logger.error(
                                    "Could not remove birthday role from %s#%s (%s)",
                                    member.name,
                                    member.discriminator,
                                    member.id,
                                    exc_info=True,
                                )
                        else:
                            # Do not remove role, wait until user rejoins, in case
                            # another cog saves roles.
                            continue

                        # Update the list.
                        await self.config.member(member).get_attr(KEY_IS_ASSIGNED).set(False)

    async def _dailyAdd(self):  # pylint: disable=too-many-branches
        """Add guild members to the birthday role."""
        guilds = self.bot.guilds

        # Avoid having data modified by other methods.
        # When we acquire the lock for all members, it also prevents lock for guild
        # from being acquired, which is what we want.
        membersLock = self.config.get_members_lock()

        async with membersLock:
            # Check each guild.
            for guild in guilds:
                # Make sure the guild is configured with birthday role.
                # If it's not, skip over it.
                bdayRoleId = await self.config.guild(guild).get_attr(KEY_BDAY_ROLE)()
                bdayChannelId = await self.config.guild(guild).get_attr(KEY_BDAY_CHANNEL)()
                if not bdayRoleId:
                    continue

                memberData = await self.config.all_members(guild)  # dict
                for memberId, memberDetails in memberData.items():
                    # If today is the user's birthday, and the role is not assigned,
                    # assign the role.

                    # Check to see that birthdate day and month have been set.
                    if (
                        memberDetails[KEY_BDAY_DAY]
                        and memberDetails[KEY_BDAY_MONTH]
                        and memberDetails[KEY_BDAY_MONTH] == int(time.strftime("%m"))
                        and memberDetails[KEY_BDAY_DAY] == int(time.strftime("%d"))
                    ):
                        # Get the necessary Discord objects.
                        role = discord.utils.get(guild.roles, id=bdayRoleId)
                        member = discord.utils.get(guild.members, id=memberId)
                        channel = discord.utils.get(guild.channels, id=bdayChannelId)

                        # Skip if member is no longer in server.
                        if not member:
                            continue

                        if not memberDetails[KEY_IS_ASSIGNED]:
                            try:
                                await member.add_roles(role)
                                self.logger.info(
                                    "Added birthday role to %s#%s (%s)",
                                    member.name,
                                    member.discriminator,
                                    member.id,
                                )
                                # Update the list.
                                await self.config.member(member).get_attr(KEY_IS_ASSIGNED).set(
                                    True
                                )

                            except discord.Forbidden:
                                self.logger.error(
                                    "Could not add role to %s#%s (%s)",
                                    member.name,
                                    member.discriminator,
                                    member.id,
                                    exc_info=True,
                                )
                            if not channel:
                                continue
                            try:
                                msg = self.getBirthdayMessage(member)
                                await channel.send(msg)
                            except discord.Forbidden:
                                self.logger.error(
                                    "Could not send message!",
                                    exc_info=True,
                                )
