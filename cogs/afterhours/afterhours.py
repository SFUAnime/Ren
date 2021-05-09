"""After hours module.

A special cog to handle the special cases for this channel.
"""
import logging
import asyncio
import discord
from discord.ext import commands
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context

AH_CHANNEL = "after-hours"
DEFAULT_GUILD = {"channelId": None, "afterHoursChannelIds": []}
STARBOARD = "highlights"


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
        ctxChannelId = await self.config.guild(ctxGuild).channelId()
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
            async with self.config.guild(channel.guild).afterHoursChannelIds() as channelIds:
                channelIds.append(channel.id)

    @commands.Cog.listener("on_guild_channel_delete")
    async def handleChannelDelete(self, channel: discord.abc.GuildChannel):
        """Listener to see if we need to remove exceptions from a channel"""
        self.logger.info(
            "Channel deletion has been detected. Name: %s, ID: %s", channel.name, channel.id
        )

        if not isinstance(channel, discord.TextChannel):
            return

        async with self.config.guild(channel.guild).afterHoursChannelIds() as channelIds:
            if channel.id in channelIds:
                self.logger.info("%s detected, removing exceptions", AH_CHANNEL)
                ctx = await self.getContext(channel)
                if not ctx:
                    return
                await self.notifyChannel(ctx, remove=True)
                await self.makeStarboardChanges(ctx, channel, remove=True)
                channelIds.remove(channel.id)

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
        await self.config.guild(ctx.guild).channelId.set(ctx.channel.id)
        await ctx.send("Using this channel to construct context later!")
