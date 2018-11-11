"""
Role Assigner cog.
Randomly assigns roles to users.
"""

import os # Used to create folder path.
import random
import itertools
import discord
from discord.ext import commands
from __main__ import send_cmd_help # pylint: disable=no-name-in-module
from .utils import config, checks # pylint: disable=relative-beyond-top-level

SAVE_FOLDER = "data/lui-cogs/roleAssigner"
MAX_LENGTH = 2000 # For a message

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating {} folder...".format(SAVE_FOLDER))
        os.makedirs(SAVE_FOLDER)

class RoleAssigner:
    """Randomly assign roles to users."""

    def __init__(self, bot):
        self.bot = bot
        self.config = config.Config("settings.json",
                                    cogname="lui-cogs/roleAssigner")
        self.roles = self.config.get("roles")

    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="roleassigner", aliases=["ra"], pass_context=True,
                    no_pm=True)
    async def roleAssigner(self, ctx):
        """Role assigner, one role per user from a list of roles."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @roleAssigner.command(name="add", pass_context=False)
    async def raAdd(self, roleName: discord.Role):
        """Add a role to be randomly assigned."""

        if not self.roles:
            self.roles = []
        elif roleName.id in self.roles:
            await self.bot.say(":warning: **Role Assigner - Add:** The role "
                               "already exists in the list!")
            return
        self.roles.append(roleName.id)

        await self.config.put("roles", self.roles)
        await self.bot.say(":white_check_mark: **Role Assigner - Add:** Role "
                           "added")

    @roleAssigner.command(name="remove", pass_context=False,
                          aliases=["del", "rm"])
    async def raRemove(self, roleName: discord.Role):
        """Remove a role to be randomly assigned."""
        if not self.roles: # pylint: disable=no-else-return
            await self.bot.say(":warning: **Role Assigner - Remove:** There are "
                               "no roles on the list.  Please add one first!")
            return
        elif roleName.id not in self.roles:
            await self.bot.say(":warning: **Role Assigner - Remove:** The role "
                               "doesn't exist on the list!")
            return

        self.roles.remove(roleName.id)
        await self.config.put("roles", self.roles)
        await self.bot.say(":white_check_mark: **Role Assigner - Remove:** "
                           "Role removed.")

    @roleAssigner.command(name="list", pass_context=True)
    async def raList(self, ctx):
        """List roles for random assignment."""
        msg = ":information_source: **Role Assigner - List:** One of the " \
              "following roles will be assigned to each user:\n"
        if not self.roles:
            await self.bot.say(":warning: **Role Assigner - List:** No roles "
                               "added!")
            return
        msg += "```\n"
        for roleId in self.roles:
            roleName = discord.utils.get(ctx.message.server.roles, id=roleId)
            msg += "{}\n".format(roleName)
        msg += "```"
        await self.bot.say(msg)

    @roleAssigner.command(name="assign", pass_context=True)
    async def raAssign(self, ctx, role: discord.Role = None):
        """
        Randomly assign roles to users.
        Optionally apply to a subset of users with a certain role.
        """
        users = ctx.message.server.members
        if role:
            users = [user for user in users if role in user.roles]
        numberOfRoles = len(self.roles)

        msgId = await self.bot.say(":hourglass: **Role Assigner - Assign:** "
                                   "Assigning roles, please wait...")

        roles = []
        roleList = ctx.message.server.roles
        for roleId in self.roles:
            roleObject = discord.utils.get(roleList, id=roleId)
            roles.append(roleObject)

        for index, user in enumerate(users):
            anyRoles = [i for i in user.roles if i in roles]
            if not anyRoles:
                await self.bot.add_roles(user, roles[index % numberOfRoles])

        msg = ":white_check_mark: **Role Assigner - Assign:** Roles assigned"
        if role:
            msg += " to users with the {} role.".format(role.name)
        else:
            msg += "."
        await self.bot.edit_message(msgId, msg)

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
