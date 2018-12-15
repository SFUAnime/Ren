import os
import logging
import time # To auto remove birthday role on the next day.
import asyncio
from datetime import datetime, timedelta
from threading import Lock
import discord
from discord.ext import commands
from cogs.utils.paginator import Pages # For making pages, requires the util!
from cogs.utils.dataIO import dataIO

# Requires checks utility from:
# https://github.com/Rapptz/RoboDanny/tree/master/cogs/utils
from cogs.utils import checks

#Global variables
KEY_BDAY_ROLE = "birthdayRole"
KEY_BDAY_USERS = "birthdayUsers"
KEY_BDAY_MONTH = "birthdateMonth"
KEY_BDAY_DAY = "birthdateDay"
KEY_IS_ASSIGNED = "isAssigned"
KEY_DATE_SET_MONTH = "dateAssignedMonth"
KEY_DATE_SET_DAY = "dateAssignedDay"
LOGGER = None
SAVE_FOLDER = "data/lui-cogs/birthday/" #Path to save folder.
SAVE_FILE = "settings.json"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

def checkFiles():
    """Used to initialize an empty database at first startup"""

    f = SAVE_FOLDER + SAVE_FILE
    if not dataIO.is_valid_json(f):
        print("Creating default birthday settings.json...")
        dataIO.save_json(f, {})


class Birthday:
    """Adds a role to someone on their birthday, and automatically remove them from
    this role after the day is over.
    """

    def loadSettings(self):
        """Loads settings from the JSON file"""
        self.settings = dataIO.load_json(SAVE_FOLDER+SAVE_FILE)

    def saveSettings(self):
        """Loads settings from the JSON file"""
        dataIO.save_json(SAVE_FOLDER+SAVE_FILE, self.settings)

    # Class constructor
    def __init__(self, bot):
        self.bot = bot

        #The JSON keys for the settings:
        self.settingsLock = Lock()

        checkFolder()
        checkFiles()
        self.loadSettings()

        # On cog load, we want the loop to run once.
        self._lastChecked = datetime.now() - timedelta(days=1)
        self._bgTask = self.bot.loop.create_task(self.birthdayLoop())

    # Cancel the background task on cog unload.
    def __unload(self):
        self._bgTask.cancel()

    @commands.group(name="birthday", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthday(self, ctx):
        """Birthday role assignment settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_birthday.command(name="setrole", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthdayRole(self, ctx, role: discord.Role):
        """Set the role to assign to a birthday user.  Make sure this role can be
        assigned and removed by the bot by placing it in the correct hierarchy location.
        """

        await self.bot.say(":white_check_mark: **Birthday - Role**: **{}** has been set "
                           "as the birthday role!".format(role.name))

        # Acquire lock and save settings to file.
        self.settingsLock.acquire()
        try:
            self.loadSettings()
            if ctx.message.server.id not in self.settings:
                self.settings[ctx.message.server.id] = {}
            self.settings[ctx.message.server.id][KEY_BDAY_ROLE] = role.id
            self.saveSettings()
        except Exception as e:
            print("Birthday Error:")
            print(e)
        finally:
            self.settingsLock.release()
        return

    @_birthday.command(name="add", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthdayAdd(self, ctx, user: discord.Member):
        """Add a user to the birthday role"""
        sid = ctx.message.server.id
        if sid not in self.settings.keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Add**: This "
                               "server is not configured, please set a role!")
            return
        elif KEY_BDAY_ROLE not in self.settings[sid].keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Add**: Please "
                               "set a role before adding a user!")
            return
        elif self.settings[sid][KEY_BDAY_ROLE] is None:
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Add**: Please "
                               "set a role before adding a user!")
            return

        try:
            # Find the Role object to add to the user.
            role = discord.utils.get(ctx.message.server.roles,
                                     id=self.settings[sid][KEY_BDAY_ROLE])

            # Add the role to the user.
            await self.bot.add_roles(user, role)
        except discord.errors.Forbidden as e:
            print("Birthday Error:")
            print(e)
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Add**: Could "
                               "not add **{}** to the list, the bot does not have enough "
                               "permissions to do so!".format(user.name))
            return

        # Save settings
        self.settingsLock.acquire()
        try:
            self.loadSettings()

            if sid not in self.settings.keys():
                self.settings[sid] = {}
            if KEY_BDAY_USERS not in self.settings[sid].keys():
                self.settings[sid][KEY_BDAY_USERS] = {}
            if user.id not in self.settings[sid][KEY_BDAY_USERS].keys():
                self.settings[sid][KEY_BDAY_USERS][user.id] = {}
            userConfig = self.settings[sid][KEY_BDAY_USERS][user.id]

            userConfig[KEY_IS_ASSIGNED] = True
            userConfig[KEY_DATE_SET_MONTH] = int(time.strftime("%m"))
            userConfig[KEY_DATE_SET_DAY] = int(time.strftime("%d"))

            self.settings[sid][KEY_BDAY_USERS][user.id] = userConfig

            self.saveSettings()
        except Exception as e:
            print("Birthday Error:")
            print(e)
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Add**: "
                               "Could not save **{}** to the list, but the role was "
                               "assigned!  Please try again.".format(user.name))
        finally:
            self.settingsLock.release()
        await self.bot.say(":white_check_mark: **Birthday - Add**: Successfully added "
                           "**{}** to the list and assigned the role.".format(user.name))

        return

    @_birthday.command(name="set", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthdaySet(self, ctx, month: int, day: int, forUser: discord.Member = None):
        """Set a user's birth date.  Defaults to you.  On the day, the bot will
        automatically add the user to the birthday role.
        """
        if forUser is None:
            forUser = ctx.message.author

        # Check inputs here.
        try:
            userBirthday = datetime(2020, month, day)
        except Exception as e:
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Set**: "
                               "Please enter a valid birthday!")
            return

        # Check if server is initialized.
        if ctx.message.server.id not in self.settings.keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Set**: "
                               "This server is not configured, please set a role!")
            return
        elif KEY_BDAY_ROLE not in self.settings[ctx.message.server.id].keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Set**: "
                               "Please notify the server admin to set a role before "
                               "continuing!")
            return
        elif self.settings[ctx.message.server.id][KEY_BDAY_ROLE] is None:
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Set**: "
                               "Please notify the server admin to set a role before "
                               "continuing!")
            return

        # Save settings
        self.settingsLock.acquire()
        try:
            self.loadSettings()
            sid = ctx.message.server.id
            if sid not in self.settings.keys():
                self.settings[sid] = {}
            if KEY_BDAY_USERS not in self.settings[sid].keys():
                self.settings[sid][KEY_BDAY_USERS] = {}
            if forUser.id not in self.settings[sid][KEY_BDAY_USERS].keys():
                self.settings[sid][KEY_BDAY_USERS][forUser.id] = {}
            self.settings[sid][KEY_BDAY_USERS][forUser.id][KEY_BDAY_MONTH] = month
            self.settings[sid][KEY_BDAY_USERS][forUser.id][KEY_BDAY_DAY] = day

            self.saveSettings()
        except Exception as e:
            print("Birthday Error:")
            print(e)
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Set**: "
                               "Could not save the birthday for **{0}** to the list. "
                               "Please try again!".format(forUser.name))
        finally:
            self.settingsLock.release()
        messageID = await self.bot.say(":white_check_mark: **Birthday - Set**: Successfully "
                                       "set **{0}**'s birthday to **{1:%B} {1:%d}**. "
                                       "The role will be assigned automatically on this "
                                       "day.".format(forUser.name, userBirthday))

        await asyncio.sleep(5)

        await self.bot.edit_message(messageID,
                                    ":white_check_mark: **Birthday - Set**: Successfully "
                                    "set **{0}**'s birthday, and the role will be automatically "
                                    "assigned on the day.".format(forUser.name, userBirthday))

        return


    @_birthday.command(name="list", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthdayList(self, ctx):
        """Lists the birthdays of users."""
        serverID = ctx.message.server.id
        serverName = ctx.message.server.name
        user = ctx.message.author

        sortedList = [] # List to sort by month, day.
        display = [] # List of text for paginator to use.  Will be constructed from sortedList.

        # Add only the users we care about (e.g. the ones that have birthdays set).
        for user, items in self.settings[serverID][KEY_BDAY_USERS].items():
            # Check if the birthdate keys exist, and they are not null.
            # If true, add an ID key and append to list.
            if KEY_BDAY_DAY in items.keys() and \
                    KEY_BDAY_MONTH in items.keys() and \
                    KEY_BDAY_DAY is not None and \
                    KEY_BDAY_MONTH is not None:
                items["ID"] = user
                sortedList.append(items)

        # Sort by month, day.
        sortedList.sort(key=lambda x: (x[KEY_BDAY_MONTH], x[KEY_BDAY_DAY]))

        for user in sortedList:
            # Get the associated user Discord object.
            userObject = discord.utils.get(ctx.message.server.members, id=user["ID"])

            # Skip if user is no longer in server.
            if userObject is None:
                continue

            # The year below is just there to accommodate leap year.  Not used anywhere else.
            userBirthday = datetime(2020, user[KEY_BDAY_MONTH], user[KEY_BDAY_DAY])
            text = "{0:%B} {0:%d}: {1}".format(userBirthday, userObject.name)
            display.append(text)

        p = Pages(self.bot, message=ctx.message, entries=display)
        p.embed.title = "Birthdays in **{}**".format(serverName)
        p.embed.colour = discord.Colour.red()
        await p.paginate()


    @_birthday.command(name="del", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def _birthdayDel(self, ctx, user: discord.Member):
        """Remove a user from the birthday role manually."""
        if ctx.message.server.id not in self.settings.keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: This "
                               "server is not configured, please set a role!")
            return
        elif KEY_BDAY_ROLE not in self.settings[ctx.message.server.id].keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: Please "
                               "set a role before removing a user from the role!")
            return
        elif self.settings[ctx.message.server.id][KEY_BDAY_ROLE] is None:
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: Please "
                               "set a role before removing a user from the role!")
            return

        if ctx.message.server.id not in self.settings.keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: The "
                               "user is not on the list!")
            return
        if KEY_BDAY_USERS not in self.settings[ctx.message.server.id].keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: The "
                               "user is not on the list!")
            return
        if user.id not in self.settings[ctx.message.server.id][KEY_BDAY_USERS].keys():
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: The "
                               "user is not on the list!")
            return


        try:
            # Find the Role object to add to the user.
            role = discord.utils.get(ctx.message.server.roles,
                                     id=self.settings[ctx.message.server.id][KEY_BDAY_ROLE])

            # Add the role to the user.
            await self.bot.remove_roles(user, role)
        except discord.errors.Forbidden as e:
            print("Birthday Error:")
            print(e)
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: "
                               "Could not remove **{}** from the role, the bot does not "
                               "have enough permissions to do so!".format(user.name))
            return

        self.settingsLock.acquire()
        try:
            self.loadSettings()
            sid = ctx.message.server.id
            self.settings[sid][KEY_BDAY_USERS][user.id][KEY_IS_ASSIGNED] = False
            self.settings[sid][KEY_BDAY_USERS][user.id][KEY_DATE_SET_MONTH] = None
            self.settings[sid][KEY_BDAY_USERS][user.id][KEY_DATE_SET_DAY] = None

            self.saveSettings()
        except Exception as e:
            print("Birthday Error:")
            print(e)
            await self.bot.say(":negative_squared_cross_mark: **Birthday - Delete**: "
                               "Could not remove **{}** from the list, but the role was "
                               "removed!  Please try again.".format(user.name))
        finally:
            self.settingsLock.release()
        await self.bot.say(":white_check_mark: **Birthday - Delete**: Successfully removed "
                           "**{}** from the list and removed the role.".format(user.name))

        return

    ########################################
    # Event loop - Try an absolute timeout #
    ########################################
    async def birthdayLoop(self):
        while self == self.bot.get_cog("Birthday"):
            if self._lastChecked.day != datetime.now().day:
                self._lastChecked = datetime.now()
                await self._dailySweep()
                await self._dailyAdd()
            await asyncio.sleep(60)

    async def _dailySweep(self):
        self.settingsLock.acquire()
        try:
            # Check each server.
            for sid in self.settings:
                # Check to see if any users need to be removed.
                for userId, userDetails in self.settings[sid][KEY_BDAY_USERS].items():
                    # If assigned and the date is different than the date assigned, remove role.
                    try:
                        if userDetails[KEY_IS_ASSIGNED]:
                            if userDetails[KEY_DATE_SET_MONTH] != int(time.strftime("%m")) or \
                                    userDetails[KEY_DATE_SET_DAY] != int(time.strftime("%d")):
                                serverObject = discord.utils.get(self.bot.servers, id=sid)
                                roleObject = discord.utils.get(serverObject.roles,
                                                               id=self.settings[sid][KEY_BDAY_ROLE])
                                userObject = discord.utils.get(serverObject.members, id=userId)

                                # Remove the role
                                try:
                                    await self.bot.remove_roles(userObject, roleObject)
                                    print("Birthday: Removing role from {}#{} ({})".format(userObject.name, userObject.discriminator, userObject.id))
                                except discord.errors.Forbidden as e:
                                    print("Birthday Error - Sweep Loop - Removing Role:")
                                    print(e)

                                # Update the list.
                                self.settings[sid][KEY_BDAY_USERS][userId][KEY_IS_ASSIGNED] = False
                                self.saveSettings()
                    except KeyError as e:
                        print("Birthday Error - Sweep Loop: Assigning key.")
                        print(e)
                        self.settings[sid][KEY_BDAY_USERS][userId][KEY_IS_ASSIGNED] = False
                        self.saveSettings()
                    except Exception as e:
                        # This happens if the isAssigned key is non-existent.
                        print("Birthday Error - Sweep Loop:")
                        print(e)
        except Exception as e:
            print("Birthday Error - Sweep Loop:")
            print(e)
        finally:
            self.settingsLock.release()

    ##################################################################
    # Event Loop - Check to see if we need to add people to the role #
    ##################################################################
    async def _dailyAdd(self):
        self.settingsLock.acquire()
        try:
            # Check each server.
            for sid in self.settings:
                # Check to see if any users need to be removed.
                for userId, userDetails in self.settings[sid][KEY_BDAY_USERS].items():
                    # If today is the user's birthday, and the role is not assigned,
                    # assign the role.

                    # Check if the keys for birthdate day and month exist, and that
                    # they're not null.
                    if KEY_BDAY_DAY in userDetails.keys() and \
                            KEY_BDAY_MONTH in userDetails.keys() and \
                            userDetails[KEY_BDAY_DAY] is not None and \
                            userDetails[KEY_BDAY_MONTH] is not None:
                        birthdayDay = userDetails[KEY_BDAY_DAY]
                        birthdayMonth = userDetails[KEY_BDAY_MONTH]

                        if birthdayMonth == int(time.strftime("%m")) and \
                                birthdayDay == int(time.strftime("%d")):
                            # Get the necessary Discord objects.
                            serverObject = discord.utils.get(self.bot.servers,
                                                             id=sid)
                            roleObject = discord.utils.get(serverObject.roles,
                                                           id=self.settings[sid][KEY_BDAY_ROLE])
                            userObject = discord.utils.get(serverObject.members,
                                                           id=userId)

                            # Skip if user is no longer in server.
                            if userObject is None:
                                continue

                            try:
                                if not currentUser[KEY_IS_ASSIGNED] and userObject is not None:
                                    try:
                                        await self.bot.add_roles(userObject, roleObject)
                                        print("Birthday: Adding role to {}#{} ({})".format(userObject.name, userObject.discriminator, userObject.id))
                                        # Update the list.
                                        userDetails[KEY_IS_ASSIGNED] = True
                                        userDetails[KEY_DATE_SET_MONTH] = int(time.strftime("%m"))
                                        userDetails[KEY_DATE_SET_DAY] = int(time.strftime("%d"))
                                        self.settings[sid][KEY_BDAY_USERS][userId] = userDetails
                                        self.saveSettings()
                                    except discord.errors.Forbidden as e:
                                        print("Birthday Error - Add Loop - Not Assigned If:")
                                        print(e)
                            except: # This key error will happen if the isAssigned key does not exist.
                                if userObject is not None:
                                    try:
                                        await self.bot.add_roles(userObject, roleObject)
                                        print("Birthday: Adding role to {}#{} ({})".format(userObject.name, userObject.discriminator, userObject.id))
                                        # Update the list.
                                        userDetails[KEY_IS_ASSIGNED] = True
                                        userDetails[KEY_DATE_SET_MONTH] = int(time.strftime("%m"))
                                        userDetails[KEY_DATE_SET_DAY] = int(time.strftime("%d"))
                                        self.settings[sid][KEY_BDAY_USERS][userId] = userDetails
                                        self.saveSettings()
                                    except discord.errors.Forbidden as e:
                                        print("Birthday Error - Add Loop - Non-existent isAssigned Key If:")
                                        print(e)

                            # End try/except block for isAssigned key.
                        # End if to check if today is the user's birthday.
                    # End if to check for birthdateMonth and birthdateDay keys.
                # End user loop.
            # End server loop.
        except Exception as e:
            print("Birthday Error - Add Loop:")
            print(e)
        finally:
            self.settingsLock.release()

def setup(bot):
    global LOGGER # pylint: disable=global-statement
    checkFolder()   #Make sure the data folder exists!
    checkFiles()    #Make sure we have settings!
    customCog = Birthday(bot)
    LOGGER = logging.getLogger("red.Birthday")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=SAVE_FOLDER+"info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    bot.add_cog(customCog)
    # bot.loop.create_task(customCog._dailyAdd())

