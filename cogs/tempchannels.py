"""Temporary channel cog.

Creates a temporary channel.
"""
import asyncio
from copy import deepcopy
import os
import json # Will need this to use in conjunction with aiohttp below.
import itertools
from threading import Lock
import time
import aiohttp # Using this to build own request to Discord API for NSFW.
import discord
from discord.ext import commands
from cogs.utils import checks, config
from cogs.utils.dataIO import dataIO

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


DEFAULT_DICT = \
{
    KEY_CH_ID: None,
    KEY_CH_NAME: "temp-channel",
    KEY_CH_TOPIC: "Created with the TempChannels cog!",
    KEY_CH_POS: 0,
    KEY_CH_CREATED: False,
    KEY_CH_CATEGORY: None,
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
    if not os.path.exists(SAVE_FOLDER):
        print("Temporary Channels: Creating folder: {} ...".format(SAVE_FOLDER))
        os.makedirs(SAVE_FOLDER)

    if not os.path.exists(SAVE_FOLDER+SAVE_FILE):
        # Build a default settings.json
        defaultDict = {KEY_SETTINGS: {}}
        dataIO.save_json(SAVE_FOLDER+SAVE_FILE, defaultDict)
        print("Temporary Channels: Creating file: {} ...".format(SAVE_FILE))

class TempChannels:
    """Creates a temporary channel."""

    def __init__(self, bot):
        self.bot = bot
        self.config = config.Config("settings.json",
                                    cogname="lui-cogs/tempchannels")
        self.lock = Lock()
        self.settings = self.config.get(KEY_SETTINGS)

    async def _sync_settings(self):
        await self.config.put(KEY_SETTINGS, self.settings)
        self.settings = self.config.get(KEY_SETTINGS)

    @commands.group(name="tempchannels", pass_context=True, no_pm=True, aliases=["tc"])
    @checks.serverowner()
    async def _tempchannels(self, ctx):
        """
        Temporary text-channel creation (only 1 at the moment).
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_tempchannels.command(name="default", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempChannelsDefault(self, ctx):
        """RUN FIRST: Sets default settings.
        - Start at 00:00.
        - Duration of channel is 1 minute.
        - The creation and deletion of TempChannel is disabled.
        - NSFW prompt will not appear.
        - TempChannel will not be role restricted.
        - If present, the previous TempChannel (if any) will be forgotten, and not deleted.
        """
        with self.lock:
            self.settings[ctx.message.server.id] = deepcopy(DEFAULT_DICT)

            await self._sync_settings()
        await self.bot.say(":white_check_mark: TempChannel: Setting default settings.")

    @_tempchannels.command(name="show", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_show(self,ctx):
        """Show current settings."""
        await self._sync_settings()
        try:
            tempCh = self.settings[ctx.message.server.id]
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
                                tempCh[KEY_ROLE_ALLOW],
                                tempCh[KEY_ROLE_DENY],
                                tempCh[KEY_CH_NAME],
                                tempCh[KEY_CH_TOPIC],
                                tempCh[KEY_CH_POS],
                                "ID {}".format(tempCh[KEY_CH_CATEGORY]) if
                                tempCh[KEY_CH_CATEGORY] else "(not set)",
                                tempCh[KEY_START_HOUR], tempCh[KEY_START_MIN],
                                tempCh[KEY_DURATION_HOURS], tempCh[KEY_DURATION_MINS]))

            await self.bot.say(msg)
        except KeyError as error:
            # LOGGER.error(error)
            await self.bot.say(":negative_squared_cross_mark: TempChannel: Cannot "
                               "display settings.  Please set default settings by "
                               "typing `{}tempchannels default` first, and then "
                               "try again.".format(ctx.prefix))

    @_tempchannels.command(name="toggle", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsToggle(self, ctx):
        """Toggle the creation/deletion of the temporary channel."""
        try:
            sid = ctx.message.server.id
            if self.settings[sid][KEY_ENABLED]:
                self.settings[sid][KEY_ENABLED] = False
                isSet = False
            else:
                self.settings[sid][KEY_ENABLED] = True
                isSet = True
        except KeyError:
            self.settings[sid][KEY_ENABLED] = True
            isSet = True
        await self._sync_settings()
        if isSet:
            await self.bot.say(":white_check_mark: TempChannel: Enabled.")
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: Disabled.")

    @_tempchannels.command(name="nsfw", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsNSFW(self, ctx):
        """Toggle NSFW requirements"""
        try:
            sid = ctx.message.server.id
            if self.settings[sid][KEY_NSFW]:
                self.settings[sid][KEY_NSFW] = False
                isSet = False
            else:
                self.settings[sid][KEY_NSFW] = True
                isSet = True
        except KeyError:
            self.settings[sid][KEY_NSFW] = True
            isSet = True
        await self._sync_settings()
        if isSet:
            await self.bot.say(":white_check_mark: TempChannel: NSFW "
                               "requirement enabled.")
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: NSFW "
                               "requirement disabled.")

    @_tempchannels.command(name="setstart", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetStart(self, ctx, hour: int, minute: int):
        """Set the temp channel creation time. Use 24 hour time.

        Parameters:
        -----------
        hour: int
            The hour to start the temporary channel.
        minute: int
            The minute to start the temporary channel.

        """
        sid = ctx.message.server.id
        if (hour > 23) or (hour < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Start "
                               "Time: Please enter a valid time.")
            return
        if (minute > 59) or (minute < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Start "
                               "Time: Please enter a valid time.")
            return

        self.settings[sid][KEY_START_HOUR] = hour
        self.settings[sid][KEY_START_MIN] = minute
        await self._sync_settings()
        await self.bot.say(":white_check_mark: TempChannel - Start Time: Start time "
                           "set to {0:002d}:{1:002d}.".format(hour,minute))

    @_tempchannels.command(name="setduration", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetDuration(self, ctx, hours: int, minutes: int):
        """
        Sets the duration of the temp channel.  Maximum 100 hours.

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
        sid = ctx.message.server.id

        if (hours >= 100) or (hours < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: "
                               "Please enter valid hours!")
            return
        elif (minutes >= 60) or (minutes < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: "
                               "Please enter valid minutes!")
            return
        elif (hours >= 99) and (minutes >= 60):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: "
                               "Please enter a valid duration!")
            return

        self.settings[sid][KEY_DURATION_HOURS] = hours
        self.settings[sid][KEY_DURATION_MINS] = minutes
        await self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Duration: Duration set to "
                           "**{0} hours, {1} minutes**.".format(hours, minutes))

    @_tempchannels.command(name="settopic", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetTopic(self, ctx, *, topic: str):
        """Sets the topic of the channel."""
        if len(topic) > MAX_CH_TOPIC:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Topic: "
                               "Topic is too long.  Try again.")
            return

        sid = ctx.message.server.id

        self.settings[sid][KEY_CH_TOPIC] = topic
        await self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Topic: Topic set to:\n"
                           "```{0}```".format(topic))

    @_tempchannels.command(name="setname", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetName(self, ctx, name: str):
        """Sets the #name of the channel."""
        if len(name) > MAX_CH_NAME:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Name: "
                               "Name is too long.  Try again.")
            return

        sid = ctx.message.server.id

        self.settings[sid][KEY_CH_NAME] = name
        await self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Name: Channel name set "
                           "to: ``{0}``".format(name))

    @_tempchannels.command(name="setposition", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetPosition(self, ctx, position: int):
        """Sets the position of the text channel in the list."""
        if position > MAX_CH_POS or position < 0:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Position: "
                               "Invalid position.  Try again.")
            return

        sid = ctx.message.server.id

        self.settings[sid][KEY_CH_POS] = position
        await self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Position: This channel "
                           "will be at position {0}".format(position))

    @_tempchannels.command(name="setcategory", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannelsSetCategory(self, ctx, categoryID: int):
        """
        Sets the parent category of the text channel (ID ONLY).

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

        self.settings[sid][KEY_CH_CATEGORY] = categoryID
        await self._sync_settings()

        if categoryID == 0:
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent "
                               "category disabled.")
        else:
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent "
                               "category set to ID `{}`.".format(categoryID))

    @_tempchannels.command(name="allowadd", pass_context=True, no_pm=True, aliases=["aa"])
    @checks.serverowner()
    async def _tempchannelsAllowAdd(self, ctx, *, role: discord.Role):
        """Add a role to allow access to the channel.

        Parameters:
        -----------
        role: discord.Role
            The role you wish to allow access to the temporary channel.

        """
        sid = ctx.message.server.id

        if role.id not in self.settings[sid][KEY_ROLE_ALLOW]:
            self.settings[sid][KEY_ROLE_ALLOW].append(role.id)
            await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`"
                               "** will be allowed access.".format(role.name))
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: "
                               "**`{0}`** is already allowed.".format(role.name))

    @_tempchannels.command(name="allowremove", pass_context=True, no_pm=True, aliases=["ar"])
    @checks.serverowner()
    async def _tempchannelsAllowRemove(self, ctx, *, role: discord.Role):
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
            return
        else:
            self.settings[sid][KEY_ROLE_ALLOW].remove(role.id)
            await self._sync_settings()
            await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`** "
                               "removed from the list.".format(role.name))

    @_tempchannels.command(name="denyadd", pass_context=True, no_pm=True, aliases=["da"])
    @checks.serverowner()
    async def _tempchannelsDenyAdd(self, ctx, *, role: discord.Role):
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
            self.settings[sid][KEY_ROLE_DENY].append(role.id)
            await self.bot.say(":white_check_mark: TempChannel - Role: **`{0}`** will "
                               "be denied message sending, provided this role is higher "
                               "than any of the ones in the allowed list.".format(role.name))
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: "
                               "**`{0}`** is already denied.".format(role))

    @_tempchannels.command(name="denyremove", pass_context=True, no_pm=True, aliases=["dr"])
    @checks.serverowner()
    async def _tempchannelsDenyRemove(self, ctx, *, role: discord.Role):
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
            self.settings[sid][KEY_ROLE_DENY].remove(role.id)
            await self._sync_settings()
            await self.bot.say(":white_check_mark: TempChannel - Role Deny: **`{0}`** "
                               "removed from the list.".format(role.name))

    @_tempchannels.command(name="delete", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_delete(self, ctx):
        """Deletes the temp channel, if it exists."""
        sid = ctx.message.server.id
        await self._sync_settings()
        if self.settings[sid][KEY_CH_CREATED]:
            # Channel created, see when we should delete it.
            if self.settings[sid][KEY_CH_ID]:
                try:
                    chanObj = self.bot.get_channel(self.settings[sid][KEY_CH_ID])
                    await self.bot.delete_channel(chanObj)
                except discord.DiscordException as error:
                    print("TempChannel: {}".format(error))
                await self.bot.say(":white_check_mark: TempChannel: Channel deleted")
            else:
                await self.bot.say(":negative_squared_cross_mark: TempChannel: No "
                                   "temporary channel to delete.")
            print("TempChannel: Channel deleted at "+format(time.strftime("%H:%M:%S")))
            self.settings[sid][KEY_CH_ID] = None
            self.settings[sid][KEY_CH_CREATED] = False
            await self._sync_settings()
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: There is no "
                               "temp channel to delete!")

    ###################
    # Background Loop #
    ###################
    async def checkChannels(self):
        """Loop to check whether or not we should create/delete the TempChannel"""
        while self == self.bot.get_cog("TempChannels"):
            await asyncio.sleep(SLEEP_TIME)
            # Create/maintain the channel during a valid time and duration, else
            # delete it.
            try:
                for sid, properties in self.settings.items():
                    missing = False
                    for key in KEYS_REQUIRED:
                        if key not in properties.keys():
                            missing = True
                            print("TempChannels: Key {} is missing in settings! Run "
                                  "[p]tc default.".format(key))
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
                        allowList = []
                        denyList = []
                        allowPerms = [discord.PermissionOverwrite(read_messages=True,
                                                                  send_messages=False)]
                        allowRoles = [self.bot.user] # Always allow the bot to read.
                        denyPerms = []
                        denyRoles = []

                        apiHeader = {"Authorization": "Bot {}".format(self.bot.settings.token),
                                     "content-type": "application/json"}

                        serverObj = self.bot.get_server(sid)

                        if properties[KEY_ROLE_ALLOW]:
                        # If we have allow roles, automatically deny @everyone the "Read
                        # Messages" permission.
                            denyPerms.append(PERMS_READ_N)
                            denyRoles.append(serverObj.default_role)
                            for allowID in properties[KEY_ROLE_ALLOW]:
                                findRole = discord.utils.get(serverObj.roles,
                                                             id=allowID)
                                allowRoles.append(findRole)

                        allowList = itertools.zip_longest(allowRoles,
                                                          allowPerms,
                                                          fillvalue=PERMS_READ_Y)

                        # Check for deny permissions.
                        if properties[KEY_ROLE_DENY]:
                            denyPerms.append(PERMS_SEND_N)
                            for denyID in properties[KEY_ROLE_DENY]:
                                findRole = discord.utils.get(serverObj.roles,
                                                             id=denyID)
                                denyRoles.append(findRole)

                        denyList = itertools.zip_longest(denyRoles,
                                                         denyPerms,
                                                         fillvalue=PERMS_SEND_N)

                        chanName = properties[KEY_CH_NAME]
                        chanObj = await self.bot.create_channel(serverObj,
                                                                chanName,
                                                                *list(allowList),
                                                                *list(denyList))

                        properties[KEY_CH_ID] = chanObj.id

                        await self._sync_settings()
                        print("TempChannels: Channel created at "+
                              format(time.strftime("%H:%M:%S")))

                        if properties[KEY_NSFW]:
                            # This is most definitely not the best way of doing it,
                            # but since we don't have a NSFW method, we have this:
                            body = {"nsfw" : True}

                            async with aiohttp.ClientSession() as session:
                                async with session.patch(PATH_CH.format(chanObj.id),
                                                         headers=apiHeader,
                                                         data=json.dumps(body)) as resp:
                                    print(resp.status)
                                    print(await resp.text())

                        # Change topic.
                        await self.bot.edit_channel(chanObj,
                                                    topic=properties[KEY_CH_TOPIC],
                                                    name=properties[KEY_CH_NAME])

                        # Set parent category.  Must use this method because library
                        # does not have a method for this yet.
                        if properties[KEY_CH_CATEGORY] != 0:
                            body = {"parent_id": properties[KEY_CH_CATEGORY]}

                            async with aiohttp.ClientSession() as session:
                                async with session.patch(PATH_CH.format(chanObj.id),
                                                         headers=apiHeader,
                                                         data=json.dumps(body)) as resp:
                                    print(resp.status)
                                    print(await resp.text())

                        # Move channel position.
                        try:
                            await self.bot.move_channel(chanObj,
                                                        properties[KEY_CH_POS])
                        except discord.DiscordException:
                            print("TempChannels: Could not move channel position")

                        # Set delete times, and save settings.
                        duration = (properties[KEY_DURATION_HOURS] * 60 * 60 +
                                    properties[KEY_DURATION_MINS] * 60)
                        properties[KEY_STOP_TIME] = time.time() + duration
                        properties[KEY_CH_CREATED] = True
                        await self._sync_settings()

                    elif properties[KEY_CH_CREATED]:
                        # Channel created, see when we should delete it.
                        await self._sync_settings()
                        if time.time() >= properties[KEY_STOP_TIME]:
                            try:
                                if properties[KEY_CH_ID]:
                                    chanObj = self.bot.get_channel(properties[KEY_CH_ID])
                                    await self.bot.delete_channel(chanObj)
                                    properties[KEY_CH_ID] = None
                            except discord.DiscordException as error:
                                print("TempChannels: {}".format(error))
                                properties[KEY_CH_ID] = None
                            print("TempChannels: Channel deleted at "+
                                  format(time.strftime("%H:%M:%S")))
                            properties[KEY_CH_CREATED] = False
                            await self._sync_settings()
            except Exception as error:
                print("TempChannels: Error! {}".format(error))

def setup(bot):
    checkFilesystem()
    tempchannels = TempChannels(bot)
    bot.add_cog(tempchannels)
    bot.loop.create_task(tempchannels.checkChannels())
