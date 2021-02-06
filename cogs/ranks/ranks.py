"""Ranks cog.
Keep track of active members on the server.
"""

import logging
import os
import random
import MySQLdb  # The use of MySQL is debatable, but will use it to incorporate CMPT 354 stuff.
import discord

from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

from .constants import *


class Ranks(commands.Cog):
    """Mee6-inspired guild rank management system.
    Not optimized for multi-guild deployments.
    """

    # Class constructor
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)
        self.config.register_global(**DEFAULT_GLOBAL)

        # TODO: Remove this later
        self.lastspoke = {}

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.Ranks")
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

    ############
    # COMMANDS #
    ############

    # [p]levels
    @commands.command(name="levels")
    @commands.guild_only()
    async def _ranksLevels(self, ctx: Context):
        """Show the server ranking leaderboard"""
        # Execute a MySQL query to order and check.

        msg = ":information_source: **Ranks - Leaderboard**\n```"
        rank = 1
        # TODO: Handle case when MySQL settings are not configured.
        database = MySQLdb.connect(
            host=await self.config.mysqlHost(),
            user=await self.config.mysqlUsername(),
            passwd=await self.config.mysqlPassword(),
        )
        cursor = database.cursor()
        cursor.execute(
            "SELECT userid, xp FROM renbot.xp WHERE guildid = "
            f"{ctx.guild.id} order by xp desc limit 20"
        )
        for row in cursor.fetchall():
            # row[0]: userID
            # row[1]: xp
            userID = row[0]
            exp = row[1]

            # Lookup the ID against the guild
            userObject = ctx.guild.get_member(userID)
            if not userObject:
                continue

            msg += str(rank).ljust(3)
            msg += (str(userObject.display_name) + " ").ljust(23)
            msg += str(exp).rjust(10) + "\n"

            rank += 1
            if rank == 11:
                break

        database.close()

        msg += "```\n Full rankings at https://ren.injabie3.moe/ranks/"
        await ctx.send(msg)

    # [p]rank
    @commands.command(name="rank")
    @commands.guild_only()
    async def _ranksCheck(
        self, ctx: Context, ofUser: discord.Member = None
    ):  # pylint: disable=too-many-locals
        """Check your rank in the server."""
        if not ofUser:
            ofUser = ctx.author

        # Execute a MySQL query to order and check.
        # TODO: Handle case when MySQL settings are not configured.
        database = MySQLdb.connect(
            host=await self.config.mysqlHost(),
            user=await self.config.mysqlUsername(),
            passwd=await self.config.mysqlPassword(),
        )
        embed = discord.Embed()
        # Using query code from:
        # https://stackoverflow.com/questions/13566695/select-increment-counter-in-mysql
        # This code is now included in the stored procedure in the database.
        cursor = database.cursor()
        cursor.execute("CALL renbot.getUserInfo({},{})".format(str(ctx.guild.id), str(ofUser.id)))
        embed = discord.Embed()
        data = cursor.fetchone()  # Data from the database.
        database.close()

        try:
            self.logger.info(data)
            rank = data[0]
            userID = data[1]
            level = data[2]
            levelXP = data[3]
            currentXP = data[4]
            totalXP = data[5]
            currentLevelXP = currentXP - totalXP
        except IndexError as error:
            await ctx.send(
                "Something went wrong when checking your level. " "Please notify the admin!"
            )
            self.logger.error(error)
            return

        userObject = ctx.guild.get_member(userID)

        embed.set_author(name=userObject.display_name, icon_url=userObject.avatar_url)
        embed.colour = discord.Colour.red()
        embed.add_field(name="Rank", value=int(rank))
        embed.add_field(name="Level", value=level)
        embed.add_field(name="Exp.", value=f"{currentLevelXP}/{levelXP} (total {currentXP})")
        embed.set_footer(text="Note: This EXP is different from Mee6.")

        await ctx.send(embed=embed)

    @commands.group(name="ranks")
    @commands.guild_only()
    async def _ranks(self, ctx: Context):
        """Mee6-inspired guild rank management system. WIP"""

    #######################
    # COMMANDS - SETTINGS #
    #######################
    # Ideally would be nice have this replaced by a web admin panel.

    # [p]ranks settings
    @_ranks.group(name="settings")
    @commands.guild_only()
    @checks.guildowner()
    async def _settings(self, ctx: Context):
        """Ranking system settings.  Only server admins should see this."""

    # [p]ranks settings default
    @_settings.command(name="default")
    @commands.guild_only()
    async def _settingsDefault(self, ctx: Context):
        """Set default for max points and cooldown."""
        await self.config.guild(ctx.guild).cooldown.set(0)
        await self.config.guild(ctx.guild).maxPoints.set(25)

        await ctx.send(
            ":information_source: **Ranks - Default:** Defaults set, run "
            f"`{ctx.prefix}rank settings show` to verify the settings."
        )

    # [p]ranks settings show
    @_settings.command(name="show")
    @commands.guild_only()
    async def _settingsShow(self, ctx: Context):
        """Show current settings."""
        cooldown = await self.config.guild(ctx.guild).cooldown()
        maxPoints = await self.config.guild(ctx.guild).maxPoints()
        msg = ":information_source: **Ranks - Current Settings**:\n```"
        msg += f"Cooldown time:  {cooldown} seconds.\n"
        msg += f"Maximum points: {maxPoints} points per eligible message```"

        await ctx.send(msg)

    # [p]rank settings cooldown
    @_settings.command(name="cooldown")
    async def _settingsCooldown(self, ctx: Context, seconds: int):
        """Set the cooldown required between EXP gains (in seconds)"""
        if seconds < 0:
            await ctx.send(
                ":negative_squared_cross_mark: **Ranks - Cooldown**: "
                "Please enter a valid time in seconds!"
            )
            return

        await self.config.guild(ctx.guild).cooldown.set(seconds)

        await ctx.send(f":white_check_mark: **Ranks - Cooldown**: Set to {seconds} seconds.")
        self.logger.info(
            "Cooldown changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        self.logger.info("Cooldown set to %s seconds", seconds)

    # [p]rank settings maxpoints
    @_settings.command(name="maxpoints")
    async def _settingsMaxpoints(self, ctx: Context, maxPoints: int = 25):
        """Set max points per eligible message. Defaults to 25 points."""
        if maxPoints < 0:
            await ctx.send(
                ":negative_squared_cross_mark: **Ranks - Max Points**: "
                "Please enter a positive number."
            )
            return

        await self.config.guild(ctx.guild).maxPoints.set(maxPoints)

        await ctx.send(
            ":white_check_mark: **Ranks - Max Points**: Users can gain "
            f"up to {maxPoiunts} points per eligible message."
        )
        self.logger.info(
            "Maximum points changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )
        self.logger.info("Maximum points per message set to %s.", maxPoints)

    # [p]rank settings dbsetup
    @_settings.command(name="dbsetup")
    @checks.guildowner()
    async def _settingsDbSetup(self, ctx):
        """Perform database set up. DO NOT USE if ranks is working."""
        await ctx.send("MySQL Set up:\n" "What is the host you wish to connect to?")

        def check(message: discord.Message):
            return message.author == ctx.message.author and message.channel == ctx.message.channel

        try:
            host = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        await ctx.send("What is the username you want to use to connect?")
        try:
            username = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        await ctx.send("What is the password you want to use to connect?")
        try:
            password = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No response received, not setting anything!")
            return

        await self.config.mysqlHost.set(host.content)
        await self.config.mysqlUsername.set(username.content)
        await self.config.mysqlPassword.set(password.content)

        await ctx.send("Settings saved.")
        self.logger.info(
            "Database connection changed by %s#%s (%s)",
            ctx.message.author.name,
            ctx.message.author.discriminator,
            ctx.message.author.id,
        )

    ####################
    # HELPER FUNCTIONS #
    ####################

    async def addPoints(self, guild, userID):
        """Add rank points between 0 and MAX_POINTS to the user"""
        maxPoints = await self.config.guild(guild).maxPoints()
        pointsToAdd = random.randint(0, maxPoints)
        if (
            not await self.config.mysqlHost()
            or not await self.config.mysqlUsername()
            or not await self.config.mysqlPassword()
        ):
            self.logger.debug("DB connection is not configured")
            return

        database = MySQLdb.connect(
            host=await self.config.mysqlHost(),
            user=await self.config.mysqlUsername(),
            passwd=await self.config.mysqlPassword(),
        )
        cursor = database.cursor()
        fetch = cursor.execute(
            "SELECT xp from renbot.xp WHERE userid = {0} and "
            "guildid = {1}".format(userID, guild.id)
        )

        currentXP = 0

        if fetch != 0:  # This user has past XP that we can add to.
            result = cursor.fetchall()
            currentXP = result[0][0] + pointsToAdd
            self.logger.debug("%s - old EXP: %s, new EXP: %s", userID, result[0][0], currentXP)
        else:  # New user
            currentXP = pointsToAdd
            self.logger.debug("%s - no EXP, new EXP: %s", userID, currentXP)

        cursor.execute(
            "REPLACE INTO renbot.xp (userid, guildid, xp) VALUES "
            f"({userID}, {guild.id}, {currentXP})"
        )
        database.commit()
        database.close()

    @commands.Cog.listener("on_message")
    async def checkFlood(self, message):
        """Check to see if the user is sending messages that are flooding the server.
        If yes, then do not add points.
        """
        # Decide whether to store last spoken user data in:
        #  - MySQL
        #  - JSON
        #  - or leave in RAM.
        # Check as follows:
        #  - Get the user ID and message time
        #  - Check the last message time that was used to add points to the current
        #    user.
        #  - If this time does not exceed COOLDOWN, return and do nothing.
        #  - If this time exceeds COOLDOWN, update the last spoken time of this user
        #    with the message time.
        #  - Add points between 0 and MAX_POINTS (use random).
        #  - Return.

        timestamp = message.created_at.timestamp()

        if message.author.bot:
            return

        if isinstance(message.channel, discord.DMChannel):
            return

        sid = message.guild.id
        uid = message.author.id

        try:
            # If the time does not exceed COOLDOWN, return and do nothing.
            cooldown = await self.config.guild(message.guild).cooldown()
            if timestamp - self.lastspoke[sid][uid]["timestamp"] <= cooldown:
                self.logger.debug("Haven't exceeded cooldown yet, returning")
                return
            # Update last spoke time with new message time.
        except KeyError:
            # Most likely key error, so create the key, then update
            # last spoke time with new message time.
            try:
                self.lastspoke[sid][uid] = {}
            except KeyError:
                self.lastspoke[sid] = {}
                self.lastspoke[sid][uid] = {}
            self.logger.error(
                "%s#%s (%s) has not spoken since last restart, adding new " "timestamp",
                message.author.name,
                message.author.discriminator,
                uid,
            )

        self.lastspoke[sid][uid]["timestamp"] = timestamp
        await self.addPoints(message.guild, message.author.id)
