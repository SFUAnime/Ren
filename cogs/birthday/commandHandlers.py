import typing

import discord

from redbot.core import checks, commands
from redbot.core.commands.context import Context

from .constants import *
from .converters import MonthDayConverter
from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="birthday")
    @commands.guild_only()
    async def _grpBirthday(self, ctx: Context):
        """Birthday role assignment settings."""

    @_grpBirthday.command(name="channel", aliases=["ch"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdSetChannel(
        self,
        ctx: Context,
        channel: typing.Optional[discord.TextChannel] = None,
    ):
        """Set the channel to mention members on their birthday.

        Parameters:
        -----------
        channel: Optional[discord.TextChannel]
            A text channel to mention a member's birthday.
        """
        await self.cmdSetChannel(ctx=ctx, channel=channel)

    @_grpBirthday.command(name="role")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdSetRole(self, ctx: Context, role: discord.Role):
        """Set the role to assign to a birthday user. Make sure this role can
        be assigned and removed by the bot by placing it in the correct
        hierarchy location.

        Parameters:
        -----------
        role: discord.Role
            A role (name or mention) to set as the birthday role.
        """
        await self.cmdSetRole(ctx=ctx, role=role)

    @_grpBirthday.command(name="test")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdTest(self, ctx: Context):
        """Test at-mentions."""
        await self.cmdTest(ctx=ctx)

    @_grpBirthday.command(name="add", aliases=["set"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdAddMemberBirthday(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        birthday: typing.Optional[MonthDayConverter],
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
        await self.cmdAddMemberBirthday(
            ctx=ctx,
            member=member,
            birthday=(
                None if birthday is None else typing.cast(MonthDayConverter.OutputType, birthday)
            ),
        )

    @_grpBirthday.command(name="list", aliases=["ls"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdListBirthdays(self, ctx: Context):
        """Lists the birthdays of users in the server."""
        await self.cmdListBirthdays(ctx=ctx)

    @_grpBirthday.command(name="unassign")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdUnassignRole(self, ctx: Context, member: discord.Member):
        """Unassign the birthday role from a user.

        Parameters:
        -----------
        member: discord.Member
            The guild member that you want to remove the birthday role from.
        """
        await self.cmdUnassignRole(ctx=ctx, member=member)

    @_grpBirthday.command(name="delete", aliases=["del", "remove", "rm"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdDeleteMemberBirthday(self, ctx: Context, member: discord.Member):
        """Delete a user's birthday role and birthday from the list.

        Parameters:
        -----------
        member: discord.Member
            The guild member whose birthday role and saved birthday you want to remove.
        """
        await self.cmdDeleteMemberBirthday(ctx=ctx, member=member)

    @_grpBirthday.group(name="self", aliases=["me"])
    @commands.guild_only()
    async def _grpSelf(self, ctx: Context):
        """Manage your birthday."""

    @_grpSelf.command("get", aliases=["display", "show"])
    @commands.guild_only()
    async def _cmdGetSelfBirthday(self, ctx: Context):
        """Display your birthday."""
        await self.cmdGetSelfBirthday(ctx=ctx, cmdSetSelfBirthday=self._cmdSetSelfBirthday)

    @_grpSelf.command("set", aliases=["add"])
    @commands.guild_only()
    async def _cmdSetSelfBirthday(self, ctx: Context, *, birthday: MonthDayConverter):
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
        await self.cmdSetSelfBirthday(
            ctx=ctx,
            birthday=typing.cast(MonthDayConverter.OutputType, birthday),
        )

    @_grpBirthday.command(name="selfbirthday")
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def _cmdToggleSelfBirthday(self, ctx: Context):
        """Allow or disallow members to set their birthdays themselves.

        If allowed, members can set their birthdays themselves ONCE, and
        ONLY IF their birthdays were not already set. Otherwise, if not
        allowed, members need to contact an administrator or a moderator
        in case they want to have their birthdays erased and/or set.
        """
        await self.cmdToggleSelfBirthday(ctx=ctx)
