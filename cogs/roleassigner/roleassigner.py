"""
Role Assigner cog.
Randomly assigns roles to users.
"""

import random
import itertools
import discord
from redbot.core import Config, checks, commands
from redbot.core.commands.context import Context
from redbot.core.utils import paginator
from redbot.core.bot import Red

SAVE_FOLDER = "data/lui-cogs/roleAssigner"
MAX_LENGTH = 2000 # For a message

KEY_ROLES = "roles"

BASE_GUILD = \
{
    KEY_ROLES: []
}

class RoleAssigner:
    """Randomly assign roles to users."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)

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
                await ctx.send(":warning: **Role Assigner - Add:** The role "
                               "already exists in the list!")
                return
            roleList.append(role.id)

            await ctx.send(":white_check_mark: **Role Assigner - Add:** Role "
                           "added")
            #TODO add modify logging statement

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
                await ctx.send(":warning: **Role Assigner - Remove:** There are "
                               "no roles on the list.  Please add one first!")
            elif role.id not in roleList:
                await ctx.send(":warning: **Role Assigner - Remove:** The role "
                               "doesn't exist on the list!")
            else:
                roleList.remove(roleName.id)
                await ctx.send(":white_check_mark: **Role Assigner - Remove:** "
                               "Role removed.")
                #TODO add modify logging statement

    @roleAssigner.command(name="list", aliases=["ls"])
    async def raList(self, ctx: Context):
        """List roles for random assignment."""
        async for self.config.guild(ctx.guild).roles() as roleList:
            msg = ":information_source: **Role Assigner - List:** One of the " \
                  "following roles will be assigned to each user:\n"
            if not roleList:
                await ctx.send(":warning: **Role Assigner - List:** No roles "
                               "added!")
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
            msgObj = await ctx.send(":hourglass: **Role Assigner - Assign:** "
                                    "Assigning roles, please wait...")

            roleObjList = []
            for roleId in self.roles:
                roleObject = discord.utils.get(ctx.guild.roles, id=roleId)
                if roleObject:
                    roleObjList.append(roleObject)

            async with ctx.typing():
                random.shuffle(members)
                # Assigning roles takes a while
                for index, member in enumerate(members):
                    anyRoles = [i for i in member.roles if i in roles]
                    if not anyRoles:
                        # Only assign one role per user. If they have one already,
                        # just skip them
                        await member.add_roles(roleObjList[index % len(roleObjList)])

            msg = ":white_check_mark: **Role Assigner - Assign:** Roles assigned"
            if role:
                msg += " to users with the {} role.".format(role.name)
            else:
                msg += "."
            await msgObj.edit(msg)

    @roleAssigner.command(name="unassign", pass_context=True)
    async def raUnassign(self, ctx, role: discord.Role = None):
        """Remove roles on the list from ALL users"""
        users = ctx.message.server.members
        if role:
            users = [user for user in users if role in user.roles]

        msgId = await self.bot.say(":hourglass: **Role Assigner - Unassign:** "
                                   "Unassigning roles, please wait...")

        roles = []
        roleList = ctx.message.server.roles
        for roleId in self.roles:
            roleObject = discord.utils.get(roleList, id=roleId)
            roles.append(roleObject)

        for userObject, roleObject in itertools.product(users, roles):
            if roleObject in userObject.roles:
                await self.bot.remove_roles(userObject, roleObject)
        msg = ":white_check_mark: **Role Assigner - Unassign:** Roles removed"
        if role:
            msg += " from users with the {} role.".format(role.name)
        else:
            msg += "."
        await self.bot.edit_message(msgId, msg)

    @roleAssigner.command(name="random", pass_context=True)
    async def raRandom(self, ctx, fromRole: discord.Role, number: int,
                       assignRole: discord.Role,
                       excludeFromRole: discord.Role = None):
        """Assign a role to some users from a certain role.

        Pick `number` of users from fromRole at random, and assign assignRole to
        those users.
        """
        if number <= 0:
            await self.bot.say(":negative_squared_cross_mark: **Role Assigner - "
                               "Random:** Please enter a positive number!")
            return

        users = ctx.message.server.members
        if excludeFromRole:
            eligibleUsers = [user for user in users if fromRole in user.roles and
                             excludeFromRole not in user.roles and assignRole not
                             in user.roles]
        else:
            eligibleUsers = [user for user in users if fromRole in user.roles and
                             assignRole not in user.roles]

        if number > len(eligibleUsers):
            # Assign role to all eligible users.
            picked = eligibleUsers
        else:
            # Randomize and select the first `number` users.
            random.shuffle(eligibleUsers)
            picked = eligibleUsers[0:number]

        if not picked:
            await self.bot.say(":negative_squared_cross_mark: **Role Assigner - "
                               "Random:** Nobody was eligible to be assigned!")
            return

        status = await self.bot.say(":hourglass: **Role Assigner - Random:** Randomly "
                                    "picking users from the role **{}** and assigning "
                                    "them to the role **{}**.  Please wait...\n"
                                    "Users being assigned:"
                                    .format(fromRole.name, assignRole.name))

        msg = "**|** "
        for user in picked:
            await self.bot.add_roles(user, assignRole)
            if len(msg) > MAX_LENGTH:
                await self.bot.say(msg)
                msg = "**|** "
            msg += "{} **|** ".format(user.name)
        await self.bot.say(msg)
        msg = (":white_check_mark: **Role Assigner - Random:** The following users "
               "were picked from the **{}** role and assigned to the role **{}**:"
               .format(fromRole.name, assignRole.name))
        await self.bot.edit_message(status, msg)

def setup(bot):
    """Add the cog to the bot."""
    checkFolder()
    bot.add_cog(RoleAssigner(bot))
