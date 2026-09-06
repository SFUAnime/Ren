import asyncio
from datetime import datetime, timedelta
import logging
import os
from random import choice
import time

import discord

from redbot.core import Config, data_manager
from redbot.core.bot import Red

from .constants import *


class Core:
    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.bgTask: asyncio.Task = None
        self.config: Config = None
        self.lastChecked: datetime = None
        self.logger: logging.Logger = None

        self.initializeConfigAndLogger()
        self.initializeBgTask()

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

    # Cancel the background task on cog unload.
    def cog_unload(self):
        self.bgTask.cancel()

    def getBirthdayMessage(self, user: discord.User) -> str:
        """Get the birthday message.

        Parameters
        ----------
        user: discord.User
            The user that we want the birthday message for.

        Returns
        -------
        str
            The birthday message, already formatted.
        """
        if self.bot.user.id == user.id:
            return BOT_BIRTHDAY_MSG
        return choice(CANNED_MESSAGES).format(user.mention)

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
