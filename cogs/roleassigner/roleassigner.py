"""Role Assigner cog.

Randomly assigns roles to users.
"""

import logging
import random
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.commands.context import Context
from .constants import *


class RoleAssigner(commands.Cog):
    """Randomly assign roles to users."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)

        self.config.register_guild(**BASE_GUILD)

        # Initialize logger and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.RoleAssigner")
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

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="roleassigner", aliases=["ra"])
    @commands.guild_only()
    async def roleAssigner(self, ctx: Context):
        """Role assigner, one role per user from a list of roles."""

    @roleAssigner.command(name="add")
    async def raAdd(self, ctx: Context, role: discord.Role):
        """Add a role to be randomly assigned.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to add to the role assigner list.
        """
        async with self.config.guild(ctx.guild).roles() as roleList:
            if role.id in roleList:
                await ctx.send(
                    ":warning: **Role Assigner - Add:** The role " "already exists in the list!"
                )
                return
            roleList.append(role.id)

            await ctx.send(":white_check_mark: **Role Assigner - Add:** Role " "added")
            self.logger.info(
                "%s#%s (%s) added the %s role.",
                ctx.author.name,
                ctx.author.discriminator,
                ctx.author.id,
                role.name,
            )

    @roleAssigner.command(name="remove", aliases=["delete", "del", "rm"])
    async def raRemove(self, ctx: Context, role: discord.Role):
        """Remove a role to be randomly assigned.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to remove from the role assigner list.
        """
        async with self.config.guild(ctx.guild).roles() as roleList:
            if not roleList:
                await ctx.send(
                    ":warning: **Role Assigner - Remove:** There are "
                    "no roles on the list.  Please add one first!"
                )
            elif role.id not in roleList:
                await ctx.send(
                    ":warning: **Role Assigner - Remove:** The role " "doesn't exist on the list!"
                )
            else:
                roleList.remove(role.id)
                await ctx.send(":white_check_mark: **Role Assigner - Remove:** " "Role removed.")
                self.logger.info(
                    "%s#%s (%s) removed the %s role.",
                    ctx.author.name,
                    ctx.author.discriminator,
                    ctx.author.id,
                    role.name,
                )

    @roleAssigner.command(name="list", aliases=["ls"])
    async def raList(self, ctx: Context):
        """List roles for random assignment."""
        async with self.config.guild(ctx.guild).roles() as roleList:
            msg = (
                ":information_source: **Role Assigner - List:** One of the "
                "following roles will be assigned to each user:\n"
            )
            if not roleList:
                await ctx.send(":warning: **Role Assigner - List:** No roles " "added!")
                return
            msg += "```\n"
            for roleId in roleList:
                roleObj = discord.utils.get(ctx.guild.roles, id=roleId)
                if roleObj:
                    msg += "{}\n".format(roleObj.name)
            msg += "```"
            await ctx.send(msg)

    @roleAssigner.command(name="assign")
    async def raAssign(self, ctx: Context, role: discord.Role = None):
        """Randomly assign roles to members of the guild.

        Parameters:
        -----------
        role: discord.Role (optional)
            Apply to a subset of users with a certain role. If this is not specified,
            then it will apply one of the roles to ALL members of the guild.
        """
        async with self.config.guild(ctx.guild).roles() as roleList:
            members = ctx.guild.members
            if role:
                members = [member for member in members if role in member.roles]
            msgObj = await ctx.send(
                ":hourglass: **Role Assigner - Assign:** " "Assigning roles, please wait..."
            )

            roleObjList = []
            for roleId in roleList:
                roleObject = discord.utils.get(ctx.guild.roles, id=roleId)
                if roleObject:
                    roleObjList.append(roleObject)

            async with ctx.typing():
                random.shuffle(members)
                # Assigning roles takes a while
                for index, member in enumerate(members):
                    anyRoles = [i for i in member.roles if i in roleObjList]
                    if not anyRoles:
                        # Only assign one role per user. If they have one already,
                        # just skip them
                        try:
                            await member.add_roles(roleObjList[index % len(roleObjList)])
                        except discord.NotFound:
                            self.logger.error(
                                "Could not assign role: Member most "
                                "likely just left the server!"
                            )

            msg = ":white_check_mark: **Role Assigner - Assign:** Roles assigned"
            if role:
                msg += " to users with the {} role.".format(role.name)
            else:
                msg += "."
            await msgObj.edit(content=msg)

    @roleAssigner.command(name="unassign")
    async def raUnassign(self, ctx: Context, role: discord.Role = None):
        """Remove roles on the list from users.

        Parameters:
        -----------
        role: discord.Role (optional)
            Remove roles from members with a certain role. If this is not specified,
            then it will remove all roles on the list from ALL members of the guild.
        """
        async with self.config.guild(ctx.guild).roles() as roleList:
            members = ctx.guild.members
            if role:
                members = [member for member in members if role in member.roles]

            msgObj = await ctx.send(
                ":hourglass: **Role Assigner - Unassign:** " "Unassigning roles, please wait..."
            )

            roleObjList = []
            for roleId in roleList:
                roleObject = discord.utils.get(ctx.guild.roles, id=roleId)
                roleObjList.append(roleObject)

            async with ctx.typing():
                for member in members:
                    try:
                        await member.remove_roles(*roleObjList)
                    except discord.NotFound:
                        self.logger.error(
                            "Could not unassign roles: Member most likely " "just left the server!"
                        )

            msg = ":white_check_mark: **Role Assigner - Unassign:** Roles removed"
            if role:
                msg += " from users with the {} role.".format(role.name)
            else:
                msg += "."
            await msgObj.edit(content=msg)

    @roleAssigner.command(name="random", pass_context=True)
    async def raRandom(
        self,
        ctx: Context,
        assignRole: discord.Role,
        number: int,
        fromRole: discord.Role = None,
        excludeFromRole: discord.Role = None,
    ):
        """Assign a role to some users from a certain role.

        Pick `number` of users from fromRole at random, and assign assignRole to
        those users.

        Parameters:
        -----------
        assignRole: discord.Role
            The role you wish to assign to those members you just picked.
        number: int
            The number of members you wish to randomly pick.
        fromRole: discord.Role (optional)
            The role you wish to pick guild members from. If this is not given,
            then it will pick from ALL guild members.
        excludeFromRole: discord.Role (optional)
            Any member with this role will not be considered for picking.
        """
        if number <= 0:
            await ctx.send(
                ":negative_squared_cross_mark: **Role Assigner - "
                "Random:** Please enter a positive number!"
            )
            return

        members = ctx.guild.members

        if excludeFromRole and fromRole:
            eligibleMembers = [
                member
                for member in members
                if fromRole in member.roles
                and excludeFromRole not in member.roles
                and assignRole not in member.roles
            ]
            msg = (
                ":hourglass: **Role Assigner - Random:** Randomly picking members "
                "from the role **{}** that do not have the role **{}** and assigning "
                "them to the role **{}**. Please wait...\nMembers being assigned:".format(
                    fromRole.name, excludeFromRole.name, assignRole.name
                )
            )
        elif fromRole:
            eligibleMembers = [
                member
                for member in members
                if fromRole in member.roles and assignRole not in member.roles
            ]
            msg = (
                ":hourglass: **Role Assigner - Random:** Randomly picking members "
                "from the role **{}** and assigning them to the role **{}**. Please "
                "wait...\nMembers being assigned:".format(fromRole.name, assignRole.name)
            )
        else:
            eligibleMembers = [member for member in members if assignRole not in member.roles]
            msg = (
                ":hourglass: **Role Assigner - Random:** Randomly picking members "
                "and assigning them to the role **{}**. Please wait...\n"
                "Members being assigned:".format(assignRole.name)
            )

        if number > len(eligibleMembers):
            # Assign role to all eligible members.
            picked = eligibleMembers
        else:
            # Randomize and select the first `number` users.
            random.shuffle(eligibleMembers)
            picked = eligibleMembers[0:number]

        if not picked:
            await ctx.send(
                ":negative_squared_cross_mark: **Role Assigner - "
                "Random:** Nobody was eligible to be assigned!"
            )
            return

        status = await ctx.send(msg)

        msg = "**|** "
        for member in picked:
            try:
                await member.add_roles(assignRole)
                if len(msg) > MAX_LENGTH:
                    await ctx.send(msg)
                    msg = "**|** "
                msg += "{} **|** ".format(member.name)
            except discord.NotFound:
                self.logger.error(
                    "Could not assign role: Member most likely just " "left the server!"
                )
        await ctx.send(msg)
        msg = (
            ":white_check_mark: **Role Assigner - Random:** The following users "
            "were assigned to the role **{}**:".format(assignRole.name)
        )
        await status.edit(content=msg)
