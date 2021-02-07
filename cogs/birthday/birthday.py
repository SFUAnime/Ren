"""Birthday cog Automatically add users to a specified birthday role on their
birthday."""
import logging
from random import choice
import time  # To auto remove birthday role on the next day.
import asyncio
from datetime import datetime, timedelta
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands.context import Context
from redbot.core.utils import paginator
from redbot.core.bot import Red
from .constants import *


class Birthday(commands.Cog):
    """Adds a role to someone on their birthday, and automatically remove them
    from this role after the day is over."""

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        # Register default (empty) settings.
        self.config.register_guild(**BASE_GUILD)
        self.config.register_member(**BASE_GUILD_MEMBER)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Birthday")
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

        # On cog load, we want the loop to run once.
        self.lastChecked = datetime.now() - timedelta(days=1)
        self.bgTask = self.bot.loop.create_task(self.birthdayLoop())

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()

    @commands.group(name="birthday")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _birthday(self, ctx: Context):
        """Birthday role assignment settings."""

    @_birthday.command(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setChannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to mention members on their birthday.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            A text channel to mention a member's birthday.
        """

        if channel:
            await self.config.guild(ctx.message.guild).birthdayChannel.set(channel.id)
            self.logger.info(
                "%s#%s (%s) set the birthday channel to %s",
                ctx.message.author.name,
                ctx.message.author.discriminator,
                ctx.message.author.id,
                channel.name,
            )
            await ctx.send(
                ":white_check_mark: **Birthday - Channel**: **{}** has been set "
                "as the birthday mention channel!".format(channel.name)
            )
        else:
            await self.config.guild(ctx.message.guild).birthdayChannel.set(None)
            await ctx.send(
                ":white_check_mark: **Birthday - Channel**: Birthday mentions are now disabled."
            )

    @_birthday.command(name="role")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def setRole(self, ctx, role: discord.Role):
        """Set the role to assign to a birthday user. Make sure this role can
        be assigned and removed by the bot by placing it in the correct
        hierarchy location.

        Parameters:
        -----------
        role: discord.Role
            A role (name or mention) to set as the birthday role.
        """

        await self.config.guild(ctx.message.guild).birthdayRole.set(role.id)
        self.logger.info(
            "%s#%s (%s) set the birthday role to %s",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            role.name,
        )
        await ctx.send(
            ":white_check_mark: **Birthday - Role**: **{}** has been set "
            "as the birthday role!".format(role.name)
        )

    @_birthday.command(name="test")
    @commands.guild_only()
    async def test(self, ctx):
        """Test at-mentions."""
        for msg in CANNED_MESSAGES:
            await ctx.send(msg.format(ctx.author.mention))

    @_birthday.command(name="add", aliases=["set"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def addMemberBirthday(
        self, ctx: Context, member: discord.Member, month: int = None, day: int = None
    ):
        """Add a user's birthday to the list. If date is not specified, it will default to the current day.
        On the day, the bot will automatically add the user to the birthday role.

        Parameters:
        -----------
        member: discord.Member
            The member whose birthday is being assigned.

        month: int (optional)
            The birthday month, between 1 and 12 inclusive.

        day: int (optional)
            The birthday day, range between 1 and 31 inclusive, depending on month.
        """
        rid = await self.config.guild(ctx.message.guild).birthdayRole()

        # Check if guild is initialized.
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Add**: "
                "This server is not configured, please set a role!"
            )
            return

        # Check if both the inputs are empty, for this case set the birthday as current day
        # If one of the parameters are missing, then raise error
        if month == None and day == None:
            day = int(time.strftime("%d"))
            month = int(time.strftime("%m"))

        elif month == None or day == None:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Add**: "
                "Please enter a valid birthday!"
            )
            return

        # Check inputs here.
        try:
            userBirthday = datetime(2020, month, day)
        except ValueError:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Add**: "
                "Please enter a valid birthday!"
            )
            return

        # Save settings
        async with self.config.member(member).all() as userConfig:
            userConfig[KEY_BDAY_MONTH] = month
            userConfig[KEY_BDAY_DAY] = day

        confMsg = await ctx.send(
            ":white_check_mark: **Birthday - Add**: Successfully "
            "added **{0}**'s birthday as **{1:%B} {1:%d}**. "
            "The role will be assigned automatically on this "
            "day.".format(member.name, userBirthday)
        )

        # Explicitly check to see if user should be added to role, if the month
        # and day just so happen to be the same as it is now.
        await self.checkBirthday()

        await asyncio.sleep(5)  # pylint: disable=no-member

        await confMsg.edit(
            content=":white_check_mark: **Birthday - Add**: Successfully "
            "added **{0}**'s birthday, and the role will be automatically "
            "assigned on the day.".format(member.name)
        )

        self.logger.info(
            "%s#%s (%s) added the birthday of %s#%s (%s) as %s",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            member.name,
            member.discriminator,
            member.id,
            userBirthday.strftime("%B %d"),
        )
        return

    @_birthday.command(name="list", aliases=["ls"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def list(self, ctx: Context):
        """Lists the birthdays of users in the server."""

        sortedList = []  # List to sort by month, day.
        display = []  # List of text for paginator to use.  Will be constructed from sortedList.

        # Add only the users we care about (e.g. the ones that have birthdays set).
        membersData = await self.config.all_members(ctx.message.guild)
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
            userObject = discord.utils.get(ctx.message.guild.members, id=user["ID"])

            # Skip if user is no longer in server.
            if not userObject:
                continue

            # The year below is just there to accommodate leap year.  Not used anywhere else.
            userBirthday = datetime(2020, user[KEY_BDAY_MONTH], user[KEY_BDAY_DAY])
            text = "{0:%B} {0:%d}: {1}".format(userBirthday, userObject.name)
            display.append(text)

        page = paginator.Pages(ctx=ctx, entries=display, show_entry_count=True)
        page.embed.title = "Birthdays in **{}**".format(ctx.message.guild.name)
        page.embed.colour = discord.Colour.red()
        await page.paginate()

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
        rid = await self.config.guild(ctx.message.guild).birthdayRole()
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Unassign**: This "
                "server is not configured, please set a role!"
            )
            return

        try:
            # Find the Role object to remove from the member.
            role = discord.utils.get(ctx.message.guild.roles, id=rid)

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

        async with self.config.member(member).all() as userConfig:
            userConfig[KEY_IS_ASSIGNED] = False

        await ctx.send(
            ":white_check_mark: **Birthday - Unassign**: Successfully "
            "unassigned **{}** from the birthday role.".format(member.name)
        )

        self.logger.info(
            "%s#%s (%s) unassigned %s#%s (%s) from the birthday role",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
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
        rid = await self.config.guild(ctx.message.guild).birthdayRole()
        if not rid:
            await ctx.send(
                ":negative_squared_cross_mark: **Birthday - Delete**: This "
                "server is not configured, please set a role!"
            )
            return

        try:
            # Find the Role object to remove from the member.
            role = discord.utils.get(ctx.message.guild.roles, id=rid)

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
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
            member.name,
            member.discriminator,
            member.id,
        )
        return

    async def checkBirthday(self):
        """Check birthday list once."""
        await self._dailySweep()
        await self._dailyAdd()

    async def birthdayLoop(self):
        """The main event loop that will call the add and sweep methods."""
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
                bdayRoleId = await self.config.guild(guild).birthdayRole()
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
                        await self.config.member(member).isAssigned.set(False)

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
                bdayRoleId = await self.config.guild(guild).birthdayRole()
                bdayChannelId = await self.config.guild(guild).birthdayChannel()
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
                                async with self.config.member(member).all() as memberConfig:
                                    memberConfig[KEY_IS_ASSIGNED] = True

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
                                msg = choice(CANNED_MESSAGES)
                                await channel.send(msg.format(member.mention))
                            except discord.Forbidden:
                                self.logger.error(
                                    "Could not send message!",
                                    exc_info=True,
                                )
