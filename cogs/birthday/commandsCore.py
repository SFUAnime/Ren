import asyncio
from datetime import date, datetime
from typing import Dict, Optional

import discord

from redbot.core import commands
from redbot.core.commands.context import Context
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.chat_formatting import bold, pagify, spoiler, warning

from .constants import *
from .core import Core


class CommandsCore(Core):
    async def cmdSetChannel(self, ctx: Context, channel: Optional[discord.TextChannel] = None):
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

    async def cmdSetRole(self, ctx: Context, role: discord.Role):
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

    async def cmdTest(self, ctx: Context):
        """Test at-mentions."""
        for msg in CANNED_MESSAGES:
            await ctx.send(msg.format(ctx.author.mention))

    async def cmdAddMemberBirthday(
        self,
        ctx: Context,
        member: discord.Member,
        birthday: Optional[datetime] = None,
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
            userConfig[KEY_ADDED_BEFORE] = True

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

    async def cmdListBirthdays(self, ctx: Context):
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

            userBirthday = datetime(DEFAULT_YEAR, user[KEY_BDAY_MONTH], user[KEY_BDAY_DAY])
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

    async def cmdUnassignRole(self, ctx: Context, member: discord.Member):
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

    async def cmdDeleteMemberBirthday(self, ctx: Context, member: discord.Member):
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

    async def cmdGetSelfBirthday(self, ctx: Context, cmdSetSelfBirthday: commands.Command):
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
            details: Dict = await birthdayConfig.all()
            if details:
                month: int = details.get(KEY_BDAY_MONTH)
                day: int = details.get(KEY_BDAY_DAY)
                if month and day:
                    birthday = date(DEFAULT_YEAR, month, day)
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
        helpSetSelfBirthdayCmdStr = f"`{ctx.clean_prefix}help {cmdSetSelfBirthday.qualified_name}`"

        replyMsg = (
            f"{headerBad}: "
            "Your birthday in this server has not been set. "
            "Please contact an administrator/moderator, or, "
            "if it is allowed by the server's admins and/or "
            "moderators, try setting it yourself. Reference "
            f"{helpSetSelfBirthdayCmdStr} for the command syntax."
        )
        await ctx.send(replyMsg)

    async def cmdSetSelfBirthday(self, ctx: Context, birthday: datetime):
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

            async def mainFlow(channel: discord.abc.Messageable, carefree: bool = False):
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
                    confirmation = await channel.send(
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
                    return msg.author == ctx.author and msg.channel == confirmation.channel

                # define response wait time
                responseTimeout = SENSITIVE_MSG_TTL + 1 if SENSITIVE_MSG_TTL else 30
                try:
                    response = await self.bot.wait_for(
                        "message", timeout=responseTimeout, check=check
                    )
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
                await mainFlow(ctx.author, carefree=True)
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

    async def cmdToggleSelfBirthday(self, ctx: Context):
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
