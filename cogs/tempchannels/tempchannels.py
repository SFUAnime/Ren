"""Temporary channel cog.

Creates a temporary channel.
"""
import json # Will need this to use in conjunction with aiohttp below.
import logging
import os
import time
import asyncio
from copy import deepcopy
import itertools
from threading import Lock
import discord
from discord.ext import commands
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context

KEY_SETTINGS = "settings"
KEY_CH_ID = "channel"
KEY_CH_TOPIC = "channelTopic"
KEY_CH_NAME = "channelName"
KEY_CH_POS = "channelPosition"
KEY_CH_CREATED = "channelCreated"
KEY_CH_CATEGORY = "channelCategory"
KEY_DURATION_HOURS = "durationHours"
KEY_DURATION_MINS = "durationMinutes"
KEY_START_HOUR = "startHour"
KEY_START_MIN = "startMinute"
KEY_STOP_TIME = "stopTime"
KEY_ENABLED = "enabled"
KEY_NSFW = "nsfw"
KEY_ROLE_ALLOW = "roleallow"
KEY_ROLE_DENY = "roledeny"

KEYS_REQUIRED = \
[KEY_CH_ID, KEY_CH_TOPIC, KEY_CH_NAME, KEY_CH_POS, KEY_CH_CREATED, KEY_CH_CATEGORY,
 KEY_DURATION_HOURS, KEY_DURATION_MINS, KEY_START_HOUR, KEY_START_MIN, KEY_ENABLED,
 KEY_NSFW, KEY_ROLE_ALLOW, KEY_ROLE_DENY]

LOGGER = None

MAX_CH_NAME = 25
MAX_CH_POS = 100
MAX_CH_TOPIC = 1024

PATH_CH = "https://discordapp.com/api/channels/{}"
PERMS_READ_Y = discord.PermissionOverwrite(read_messages=True, add_reactions=False)
PERMS_READ_N = discord.PermissionOverwrite(read_messages=False, add_reactions=False)
PERMS_SEND_N = discord.PermissionOverwrite(send_messages=False, add_reactions=False)

SAVE_FOLDER = "data/lui-cogs/tempchannels/"
SAVE_FILE = "settings.json"
SLEEP_TIME = 15 # Background loop sleep time in seconds


DEFAULT_GUILD = \
{
    KEY_CH_ID: None,
    KEY_CH_NAME: "temp-channel",
    KEY_CH_TOPIC: "Created with the TempChannels cog!",
    KEY_CH_POS: 0,
    KEY_CH_CREATED: False,
    KEY_CH_CATEGORY: 0,
    KEY_DURATION_HOURS: 0,
    KEY_DURATION_MINS: 1,
    KEY_START_HOUR: 20,
    KEY_START_MIN: 0,
    KEY_ENABLED: False,
    KEY_NSFW: False,
    KEY_ROLE_ALLOW: [],
    KEY_ROLE_DENY: []
}

def checkFilesystem():
    """Check if the folders/files are created."""
    if not os.path.exists(SAVE_FOLDER):
        print("Temporary Channels: Creating folder: {} ...".format(SAVE_FOLDER))
        os.makedirs(SAVE_FOLDER)

    if not os.path.exists(SAVE_FOLDER+SAVE_FILE):
        # Build a default settings.json
        defaultDict = {KEY_SETTINGS: {}}
        dataIO.save_json(SAVE_FOLDER+SAVE_FILE, defaultDict)
        print("Temporary Channels: Creating file: {} ...".format(SAVE_FILE))

def _createPermList(serverRoleList, roleIdList, perms):
    """Create a list to use with discord permissions.

    Parameters:
    -----------
    serverRoleList: [discord.Role]
        The entire iterable of the roles for a particular server.  Use the one given
        from discord.Server.roles.
    roleIdList: [int]
        The list of role IDs that we want the same permissions for.
    perms: discord.PermissionsOverwrite
        The permissions for these roles, all of which will have the same permissions

    Returns:
    --------
    permList: [(discord.Role, discord.PermissionsOverwrite)]
        A list of tuples that can directly be given to discord.Client.create_channel().
    """
    roleList = []
    tupleList = []
    for roleID in roleIdList:
        findRole = discord.utils.get(serverRoleList,
                                     id=roleID)
        if findRole:
            roleList.append(findRole)

    tupleList = itertools.zip_longest(roleList,
                                      [],
                                      fillvalue=perms)
    return tupleList


class TempChannels(commands.Cog):
    """Creates a temporary channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self,
                                      identifier=5842647,
                                      force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)
        self.lock = Lock()
        self.settings = self.config.get(KEY_SETTINGS)

    async def _syncSettings(self):
        """Force settings to file and reload"""
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
        rolesAllow = [discord.utils.get(ctx.guild.roles,
                                        id=rid) for rid in tempCh[KEY_ROLE_ALLOW]]
        rolesAllow = [roleName.name for roleName in rolesAllow if roleName]
        rolesDeny = [discord.utils.get(ctx.guild.roles,
                                       id=rid) for rid in tempCh[KEY_ROLE_DENY]]
        rolesDeny = [roleName.name for roleName in rolesDeny if roleName]
        msg = (":information_source: TempChannel - Current Settings\n```"
               "Enabled?       {}\n"
               "NSFW Prompt:   {}\n"
               "Roles Allowed: {}\n"
               "Roles Denied:  {}\n"
               "Ch. Name:      #{}\n"
               "Ch. Topic:     {}\n"
               "Ch. Position:  {}\n"
               "Ch. Category:  {}\n"
               "Creation Time: {:002d}:{:002d}\n"
               "Duration:      {}h {}m"
               "```".format("Yes" if tempCh[KEY_ENABLED] else "No",
                            "Yes" if tempCh[KEY_NSFW] else "No",
                            rolesAllow,
                            rolesDeny,
                            tempCh[KEY_CH_NAME],
                            tempCh[KEY_CH_TOPIC],
                            tempCh[KEY_CH_POS],
                            "ID {}".format(tempCh[KEY_CH_CATEGORY]) if
                            tempCh[KEY_CH_CATEGORY] else "(not set)",
                            tempCh[KEY_START_HOUR], tempCh[KEY_START_MIN],
                            tempCh[KEY_DURATION_HOURS], tempCh[KEY_DURATION_MINS]))

        await ctx.send(msg)

    @tempChannels.command(name="toggle")
    async def tempChannelsToggle(self, ctx: Context):
        """Toggle the creation/deletion of the temporary channel."""
        async with self.config.guild(ctx.guild).enabled as enabled:
            if enabled:
                enabled = False
                LOGGER.info("%s (%s) DISABLED the temp channel for %s (%s)",
                            ctx.author.name, ctx.author.id,
                            ctx.guild.name, ctx.guild.id)
                await ctx.send(":negative_squared_cross_mark: TempChannel: Disabled.")
            else:
                enabled = True
                LOGGER.info("%s (%s) ENABLED the temp channel for %s (%s)",
                            ctx.author.name, ctx.author.id,
                            ctx.guild.name, ctx.guild.id)
                await ctx.send(":white_check_mark: TempChannel: Enabled.")

    @tempChannels.command(name="nsfw")
    async def tempChannelsNSFW(self, ctx: Context):
        """Toggle NSFW requirements"""
        async with self.config.guild(ctx.guild).nsfw() as nsfw:
            sid = ctx.message.server.id
            if nsfw:
                nsfw = False
                LOGGER.info("%s (%s) DISABLED the NSFW prompt for %s (%s)",
                            ctx.message.author.name, ctx.message.author.id,
                            ctx.message.server.name, ctx.message.author.id)
                await ctx.send(":negative_squared_cross_mark: TempChannel: NSFW "
                               "requirement disabled.")
            else:
                nsfw = True
                LOGGER.info("%s (%s) ENABLED the NSFW prompt for %s (%s)",
                            ctx.author.name, ctx.author.id,
                            ctx.guild.name, ctx.guild.id)
                await ctx.send(":white_check_mark: TempChannel: NSFW "
                               "requirement enabled.")

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
            await ctx.send(":negative_squared_cross_mark: TempChannel - Start "
                           "Time: Please enter a valid time.")
            return
        if (minute > 59) or (minute < 0):
            await ctx.send(":negative_squared_cross_mark: TempChannel - Start "
                           "Time: Please enter a valid time.")
            return

        async with self.config.guild(guild).all() as guildData:
            guildData[KEY_START_HOUR] = hour
            guildData[KEY_START_MIN] = minute
        LOGGER.info("%s (%s) set the start time to %002d:%002d on %s (%s)",
                    ctx.author.name, ctx.author.id,
                    hour, minute, ctx.guild.name, ctx.guild.id)
        await ctx.send(":white_check_mark: TempChannel - Start Time: Start time "
                       "set to {0:002d}:{1:002d}.".format(hour, minute))

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
            await ctx.send(":negative_squared_cross_mark: TempChannel - Duration: "
                           "Please enter valid hours!")
            return
        if (minutes >= 60) or (minutes < 0):
            await ctx.send(":negative_squared_cross_mark: TempChannel - Duration: "
                           "Please enter valid minutes!")
            return
        if (hours >= 99) and (minutes >= 60):
            await ctx.send(":negative_squared_cross_mark: TempChannel - Duration: "
                           "Please enter a valid duration!")
            return

        async with self.config.guild(ctx.guild).all() as guildData:
            guildData[KEY_DURATION_HOURS] = hours
            guildData[KEY_DURATION_MINS] = minutes
        LOGGER.info("%s (%s) set the duration to %s hours, %s minutes on %s (%s)",
                    ctx.author.name, ctx.author.id,
                    hours, minutes, ctx.guild.name, ctx.guild.id)

        await ctx.send(":white_check_mark: TempChannel - Duration: Duration set to "
                       "**{0} hours, {1} minutes**.".format(hours, minutes))

    @tempChannels.command(name="topic")
    async def tempChannelsTopic(self, ctx: Context, *, topic: str):
        """Set the topic of the channel.

        Parameters:
        -----------
        topic: str
            The topic of the channel.
        """
        if len(topic) > MAX_CH_TOPIC:
            await ctx.send(":negative_squared_cross_mark: TempChannel - Topic: "
                           "Topic is too long.  Try again.")
            return

        await self.config.guild(ctx.guild).channelTopic.set(topic)

        LOGGER.info("%s (%s) set the channel topic to the following on %s (%s): %s",
                    ctx.author.name, ctx.author.id,
                    ctx.guild.name, ctx.guild.id, topic)

        await ctx.send(":white_check_mark: TempChannel - Topic: Topic set to:\n"
                       "```{0}```".format(topic))

    @tempChannels.command(name="name")
    async def tempChannelsName(self, ctx, name: str):
        """Set the #name of the channel.

        Parameters:
        -----------
        name: str
            The #name of the channel, which is shown on the left panel of Discord.
        """
        if len(name) > MAX_CH_NAME:
            await ctx.send(":negative_squared_cross_mark: TempChannel - Name: "
                           "Name is too long.  Try again.")
            return

        await self.config.guild(ctx.guild).channelName.set(name)

        LOGGER.info("%s (%s) set the channel name to ""%s"" on %s (%s)",
                    ctx.author.name, ctx.author.id,
                    name, ctx.guild.name, ctx.guild.id)

        await ctx.send(":white_check_mark: TempChannel - Name: Channel name set "
                       "to: ``{0}``".format(name))

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
            await ctx.send(":negative_squared_cross_mark: TempChannel - Position: "
                           "Invalid position.  Try again.")
            return

        await self.config.guild(ctx.guild).channelPosition.set(position)
        LOGGER.info("%s (%s) changed the position to %s on %s (%s)",
                    ctx.author.name, ctx.author.id,
                    position, ctx.guild.name, ctx.guild.id)

        await ctx.send(":white_check_mark: TempChannel - Position: This channel "
                       "will be at position {0}".format(position))

    @tempChannels.command(name="category", pass_context=True, no_pm=True)
    async def tempChannelsCategory(self, ctx, categoryID: int):
        """Set the parent category of the text channel (ID ONLY).

        Since the library does not support categories yet, we will use IDs.
        To retreive an ID:
        - Turn on Developer Mode.
        - Right click the category.
        - Click "Copy ID"
        - Run this command with the ID.

        Note: This is an advanced command. No error checking is done for this! Ensure
        that the ID is correct, or else the temporary channel may not show up!

        Parameters:
        -----------
        categoryID: int
            The category ID you wish to nest the temporary channel under. Enter 0
            to disable category nesting.
        """
        if categoryID < 0:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Category: "
                               "Please enter a valid ID.")
            return

        sid = ctx.message.server.id

        with self.lock:
            self.settings[sid][KEY_CH_CATEGORY] = categoryID
            await self._syncSettings()

        if categoryID == 0:
            LOGGER.info("%s (%s) disabled category nesting on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent "
                               "category disabled.")
        else:
            LOGGER.info("%s (%s) set the parent category ID to %s on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        categoryID, ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent "
                               "category set to ID `{}`.".format(categoryID))

    @tempChannels.command(name="allowadd", pass_context=True, no_pm=True, aliases=["aa"])
    async def tempChannelsAllowAdd(self, ctx, *, role: discord.Role):
        """Add a role to allow access to the channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to allow access to the temporary channel.

        """
        sid = ctx.message.server.id

        if role.id not in self.settings[sid][KEY_ROLE_ALLOW]:
            with self.lock:
                self.settings[sid][KEY_ROLE_ALLOW].append(role.id)
                await self._syncSettings()
            LOGGER.info("%s (%s) added role %s to the allow list on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        role.name, ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`"
                               "** will be allowed access.".format(role.name))
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: "
                               "**`{0}`** is already allowed.".format(role.name))

    @tempChannels.command(name="allowremove", pass_context=True, no_pm=True, aliases=["ar"])
    async def tempChannelsAllowRemove(self, ctx, *, role: discord.Role):
        """Remove a role from being able access the temporary channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to remove access from.
        """
        sid = ctx.message.server.id

        if not self.settings[sid][KEY_ROLE_ALLOW] or \
                role.id not in self.settings[sid][KEY_ROLE_ALLOW]:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: "
                               "**`{0}`** wasn't on the list.".format(role.name))
        else:
            with self.lock:
                self.settings[sid][KEY_ROLE_ALLOW].remove(role.id)
                await self._syncSettings()
            LOGGER.info("%s (%s) removed role %s from the allow list on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        role.name, ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`** "
                               "removed from the list.".format(role.name))

    @tempChannels.command(name="denyadd", pass_context=True, no_pm=True, aliases=["da"])
    async def tempChannelsDenyAdd(self, ctx, *, role: discord.Role):
        """Add a role to block sending message to the channel.

        This role should be HIGHER in the role hierarchy than the roles in
        the allowed list!  The bot will not check for this.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to deny sending permissions in the temporary channel.
        """
        sid = ctx.message.server.id

        if role.id not in self.settings[sid][KEY_ROLE_DENY]:
            with self.lock:
                self.settings[sid][KEY_ROLE_DENY].append(role.id)
                await self._syncSettings()
            LOGGER.info("%s (%s) added role %s to the deny list on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        role.name, ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Role: **`{0}`** will "
                               "be denied message sending, provided this role is higher "
                               "than any of the ones in the allowed list.".format(role.name))
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: "
                               "**`{0}`** is already denied.".format(role))

    @tempChannels.command(name="denyremove", pass_context=True, no_pm=True, aliases=["dr"])
    async def tempChannelsDenyRemove(self, ctx, *, role: discord.Role):
        """Remove role from being blocked sending to the channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to remove from the deny list.
        """
        sid = ctx.message.server.id

        if not self.settings[sid][KEY_ROLE_DENY] or \
                role.id not in self.settings[sid][KEY_ROLE_DENY]:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: "
                               "**`{0}`** wasn't on the list.".format(role.name))
        else:
            with self.lock:
                self.settings[sid][KEY_ROLE_DENY].remove(role.id)
                await self._syncSettings()
            LOGGER.info("%s (%s) removed role %s from the deny list on %s (%s)",
                        ctx.message.author.name, ctx.message.author.id,
                        role.name, ctx.message.server.name, sid)
            await self.bot.say(":white_check_mark: TempChannel - Role Deny: **`{0}`** "
                               "removed from the list.".format(role.name))

    @tempChannels.command(name="delete", pass_context=True, no_pm=True)
    async def tempChannelsDelete(self, ctx):
        """Deletes the temp channel, if it exists."""
        sid = ctx.message.server.id
        await self._syncSettings()
        if self.settings[sid][KEY_CH_CREATED]:
            # Channel created, see when we should delete it.
            if self.settings[sid][KEY_CH_ID]:
                try:
                    chanObj = self.bot.get_channel(self.settings[sid][KEY_CH_ID])
                    await self.bot.delete_channel(chanObj)
                except discord.DiscordException:
                    LOGGER.error("Could not delete channel!", exc_info=True)
                finally:
                    with self.lock:
                        self.settings[sid][KEY_CH_ID] = None
                        self.settings[sid][KEY_CH_CREATED] = False
                        await self._syncSettings()
                    LOGGER.info("Channel #%s (%s) in %s (%s) was deleted by %s (%s).",
                                chanObj.name, chanObj.id,
                                ctx.message.server.name, ctx.message.server.id,
                                ctx.message.author.name, ctx.message.author.id)
                await self.bot.say(":white_check_mark: TempChannel: Channel deleted")
            else:
                await self.bot.say(":negative_squared_cross_mark: TempChannel: No "
                                   "temporary channel to delete.")
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: There is no "
                               "temp channel to delete!")

    ###################
    # Background Loop #
    ###################
    async def checkChannels(self): # pylint: disable=too-many-branches,too-many-statements
        """Loop to check whether or not we should create/delete the TempChannel"""
        while self == self.bot.get_cog("TempChannels"):
            await asyncio.sleep(SLEEP_TIME)
            # Create/maintain the channel during a valid time and duration, else
            # delete it.
            with self.lock:
                for sid, properties in self.settings.items():
                    try:
                        serverObj = self.bot.get_server(sid)

                        missing = False

                        for key in KEYS_REQUIRED:
                            if key not in properties.keys():
                                missing = True
                                LOGGER.error("Key %s is missing in settings for server "
                                             "%s (%s)! Run [p]tc default first!",
                                             key, serverObj.name, serverObj.id)

                        if missing or not properties[KEY_ENABLED]:
                            continue

                        if int(time.strftime("%H")) == properties[KEY_START_HOUR] and \
                                int(time.strftime("%M")) == properties[KEY_START_MIN] and \
                                not properties[KEY_CH_CREATED] and \
                                not properties[KEY_CH_ID]:
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

                            apiHeader = {"Authorization": "Bot {}".format(self.bot.settings.token),
                                         "content-type": "application/json"}
                            # Always allow the bot to read.
                            allowList = [(self.bot.user, PERMS_READ_Y)]
                            denyList = []
                            body = {}

                            if properties[KEY_ROLE_ALLOW]:
                            # If we have allow roles, automatically deny @everyone the "Read
                            # Messages" permission.
                                denyList.append((serverObj.default_role,
                                                 PERMS_READ_N))
                                allowList.extend(_createPermList(serverObj.roles,
                                                                 properties[KEY_ROLE_ALLOW],
                                                                 PERMS_READ_Y))

                            # Check for deny permissions.
                            if properties[KEY_ROLE_DENY]:
                                denyList.extend(_createPermList(serverObj.roles,
                                                                properties[KEY_ROLE_DENY],
                                                                PERMS_SEND_N))

                            chanObj = await self.bot.create_channel(serverObj,
                                                                    properties[KEY_CH_NAME],
                                                                    *list(allowList),
                                                                    *list(denyList))

                            properties[KEY_CH_ID] = chanObj.id

                            LOGGER.info("Channel #%s (%s) in %s (%s) was created.",
                                        chanObj.name, chanObj.id,
                                        serverObj.name, serverObj.id)

                            if properties[KEY_NSFW]:
                                body["nsfw"] = True

                            if properties[KEY_CH_CATEGORY] != 0:
                                body["parent_id"] = properties[KEY_CH_CATEGORY]

                            if body:
                                # Set nsfw and/or arent category. Must use this method
                                # because this version of the discord.py library does not
                                # have a method for this yet.
                                async with aiohttp.ClientSession() as session:
                                    async with session.patch(PATH_CH.format(chanObj.id),
                                                             headers=apiHeader,
                                                             data=json.dumps(body)) as resp:
                                        LOGGER.debug("API status code: %s", resp.status)
                                        LOGGER.debug("API response: %s", await resp.text())

                            # Change topic.
                            await self.bot.edit_channel(chanObj,
                                                        topic=properties[KEY_CH_TOPIC],
                                                        name=properties[KEY_CH_NAME])

                            # Move channel position.
                            try:
                                await self.bot.move_channel(chanObj,
                                                            properties[KEY_CH_POS])
                            except discord.DiscordException:
                                LOGGER.error("Could not move channel position for %s (%s)!",
                                             serverObj.name, serverObj.id, exc_info=True)

                            # Set delete times, and save settings.
                            duration = (properties[KEY_DURATION_HOURS] * 60 * 60 +
                                        properties[KEY_DURATION_MINS] * 60)
                            properties[KEY_STOP_TIME] = time.time() + duration
                            properties[KEY_CH_CREATED] = True

                        elif properties[KEY_CH_CREATED]:
                            # Channel created, see when we should delete it.
                            if time.time() >= properties[KEY_STOP_TIME]:
                                chanObj = self.bot.get_channel(properties[KEY_CH_ID])
                                properties[KEY_CH_ID] = None
                                properties[KEY_CH_CREATED] = False

                                if chanObj:
                                    await self.bot.delete_channel(chanObj)

                                LOGGER.info("Channel #%s (%s) in %s (%s) was deleted.",
                                            chanObj.name, chanObj.id,
                                            serverObj.name, serverObj.id)
                        await self._syncSettings()
                    except Exception: # pylint: disable=broad-except
                        LOGGER.error("Something went terribly wrong for server %s (%s)!",
                                     exc_info=True)

def setup(bot):
    """Add the cog to the bot."""
    global LOGGER # pylint: disable=global-statement
    checkFilesystem()
    tempchannels = TempChannels(bot)
    LOGGER = logging.getLogger("red.TempChannels")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=SAVE_FOLDER+"info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    bot.add_cog(tempchannels)
    bot.loop.create_task(tempchannels.checkChannels())
