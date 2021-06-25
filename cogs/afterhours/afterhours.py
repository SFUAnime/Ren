"""After hours module.

A special cog to handle the special cases for this channel.
"""
import logging
from datetime import datetime, timedelta
import asyncio
import discord
from discord.ext import commands
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

AH_CHANNEL = "after-hours"
KEY_CTX_CHANNEL_ID = "channelId"
KEY_CHANNEL_IDS = "channelIds"
DEFAULT_GUILD = {KEY_CTX_CHANNEL_ID: None, KEY_CHANNEL_IDS: {}}
STARBOARD = "highlights"
DELETE_TIME = 32 * 60 * 60
SLEEP_TIME = 60 * 60


class AfterHours(commands.Cog):
    """Special casing galore!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.AfterHours")
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
        self.bgTask = self.bot.loop.create_task(self.backgroundLoop())

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        self.logger.info("Unloading cog")
        self.bgTask.cancel()

    def cog_unload(self):
        self.logger.info("Unloading cog")
        self.__unload()

    async def backgroundLoop(self):
        """Background loop to garbage collect"""
        while True:
            self.logger.debug("Checking to see if we need to garbage collect")
            for guild in self.bot.guilds:
                self.logger.debug("Checking guild %s", guild.id)
                async with self.config.guild(guild).get_attr(KEY_CHANNEL_IDS)() as channels:
                    staleIds = []
                    for channelId, data in channels.items():
                        self.logger.debug("Checking channel ID %s", channelId)
                        channel = discord.utils.get(guild.channels, id=int(channelId))
                        if not channel:
                            self.logger.error("Channel ID %s doesn't exist!", channelId)
                            staleIds.append(channelId)
                            continue
                        creationTime = datetime.fromtimestamp(data["time"])
                        self.logger.debug("Time difference = %s", datetime.now() - creationTime)
                        if datetime.now() - creationTime > timedelta(seconds=DELETE_TIME):
                            self.logger.info("Deleting channel %s (%s)", channel.name, channel.id)
                            await channel.delete(reason="AfterHours purge")
                            # Don't delete the ID here, this will be taken care of in
                            # the delete listener
                    for channelId in staleIds:
                        self.logger.info("Purging stale channel ID %s", channelId)
                        del channels[channelId]
            await asyncio.sleep(SLEEP_TIME)

    async def getContext(self, channel: discord.TextChannel):
        """Get the Context object from a text channel.

        Parameters
        ----------
        channel: discord.TextChannel
            The text channel to use in order to create the Context object.

        Returns
        -------
        ctx: Context
            The context needed to send messages and invoke methods from other cogs.
        """
        ctxGuild = channel.guild
        ctxChannelId = await self.config.guild(ctxGuild).get_attr(KEY_CTX_CHANNEL_ID)()
        ctxChannel = discord.utils.get(ctxGuild.channels, id=ctxChannelId)
        if not ctxChannel:
            self.logger.error("Cannot find channel to construct context!")
            return None
        async for message in ctxChannel.history(limit=1):
            lastMessage = message
        return await self.bot.get_context(lastMessage)

    async def makeStarboardChanges(
        self, ctx: Context, channel: discord.abc.GuildChannel, remove=False
    ):
        """Apply Starboard changes.

        Parameters
        -----------
        ctx: Context
            The Context object in order to invoke commands
        channel: discord.abc.GuildChannel
            The channel to apply Starboard changes to.
        remove: bool
            Indicate whether we want to remove the changes. Defaults to False.
        """
        self.logger.info("Applying/removing Starboard exceptions, remove=%s", remove)
        sbCog = self.bot.get_cog("Starboard")
        if not sbCog:
            self.logger.error("Starboard not loaded. skipping")
            return

        try:
            starboard = sbCog.starboards[ctx.guild.id]["highlights"]
        except KeyError:
            self.logger.error("Cannot get the starboard!")

        if remove:
            await ctx.invoke(sbCog.blacklist_remove, starboard=starboard, channel_or_role=channel)
        else:
            await ctx.invoke(sbCog.blacklist_add, starboard=starboard, channel_or_role=channel)

    async def notifyChannel(self, ctx, remove=False):
        if remove:
            await ctx.send(f":information_source: **{AH_CHANNEL} removed, removing exceptions**")
        else:
            await ctx.send(f":information_source: **{AH_CHANNEL} created, adding exceptions**")

    async def makeWordFilterChanges(
        self, ctx: Context, channel: discord.abc.GuildChannel, remove=False
    ):
        """Apply WordFilter changes.

        Parameters
        -----------
        ctx: Context
            The Context object in order to invoke commands
        channel: discord.abc.GuildChannel
            The channel to apply WordFilter changes to.
        remove: bool
            Indicate whether we want to remove the changes. Defaults to False.
        """
        self.logger.info("Applying/removing WordFilter exceptions, remove=%s", remove)
        cog = self.bot.get_cog("WordFilter")
        if not cog:
            self.logger.error("WordFilter not loaded. skipping")
            return

        if remove:
            await ctx.invoke(cog._channelRemove, channel=channel)
        else:
            await ctx.invoke(cog._channelAdd, channel=channel)

    @commands.Cog.listener("on_guild_channel_create")
    async def handleChannelCreate(self, channel: discord.abc.GuildChannel):
        """Listener to see if we need to add exceptions to a channel"""
        self.logger.info(
            "Channel creation has been detected. Name: %s, ID: %s", channel.name, channel.id
        )

        if not isinstance(channel, discord.TextChannel):
            return

        if channel.name == AH_CHANNEL:
            self.logger.info("%s detected, applying exceptions", AH_CHANNEL)
            ctx = await self.getContext(channel)
            if not ctx:
                return
            await self.notifyChannel(ctx)
            await self.makeStarboardChanges(ctx, channel)
            await self.makeWordFilterChanges(ctx, channel)
            async with self.config.guild(channel.guild).get_attr(KEY_CHANNEL_IDS)() as channelIds:
                channelIds[channel.id] = {"time": datetime.now().timestamp()}

    @commands.Cog.listener("on_guild_channel_delete")
    async def handleChannelDelete(self, channel: discord.abc.GuildChannel):
        """Listener to see if we need to remove exceptions from a channel"""
        self.logger.info(
            "Channel deletion has been detected. Name: %s, ID: %s", channel.name, channel.id
        )

        if not isinstance(channel, discord.TextChannel):
            return

        async with self.config.guild(channel.guild).get_attr(KEY_CHANNEL_IDS)() as channelIds:
            if str(channel.id) in channelIds:
                self.logger.info("%s detected, removing exceptions", AH_CHANNEL)
                ctx = await self.getContext(channel)
                if not ctx:
                    return
                await self.notifyChannel(ctx, remove=True)
                await self.makeStarboardChanges(ctx, channel, remove=True)
                await self.makeWordFilterChanges(ctx, channel, remove=True)
                del channelIds[str(channel.id)]

    @commands.group(name="afterhours")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def afterHours(self, ctx: Context):
        """Configure after-hours exceptions

        There's nothing configurable from Discord.
        """

    @afterHours.command(name="set")
    async def afterHoursSet(self, ctx: Context):
        """Set the channel for notifications."""
        await self.config.guild(ctx.guild).get_attr(KEY_CTX_CHANNEL_ID).set(ctx.channel.id)
        await ctx.send("Using this channel to construct context later!")
