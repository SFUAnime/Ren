"""Download avatars when people change them."""
from datetime import datetime
import logging
import pathlib
import discord
from redbot.core import checks, commands, data_manager
from redbot.core.commands.context import Context
from redbot.core.bot import Red


class Avatar(commands.Cog):
    """The Avatar collector."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.luicogs.Avatar")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename=str(self.saveFolder) + "/info.log", encoding="utf-8", mode="a"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
            )
            self.logger.addHandler(handler)

    @commands.group(name="avatar")
    @checks.mod_or_permissions()
    @commands.guild_only()
    async def _avatar(self, ctx: Context):
        """Avatar commands."""

    @_avatar.command(name="save")
    async def _saveAvatars(self, ctx: Context):
        """Save all avatars in the current guild."""
        async with ctx.typing():
            for member in ctx.guild.members:
                await self.saveAvatar(member)
            await ctx.send("Saved all avatars!")

    @commands.Cog.listener("on_user_update")
    async def newAvatarListener(self, oldUser, updatedUser):
        """Listener for user updates."""
        if oldUser.avatar == updatedUser.avatar:
            return

        self.logger.info(
            "%s#%s (%s) updated their avatar, saving image",
            updatedUser.name,
            updatedUser.discriminator,
            updatedUser.id,
        )
        await self.saveAvatar(updatedUser)

    async def saveAvatar(self, user: discord.User):
        """Save avatar images to the cog folder.

        Parameters
        ----------
        user: discord.User
            The user of which you wish to save the avatar for.
        """
        avatar = user.avatar_url_as(format="png")
        currentTime = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = "{}/{}".format(self.saveFolder, user.id)
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        filepath = "{}/{}_{}.png".format(path, user.id, currentTime)
        await avatar.save(filepath)
        self.logger.debug("Saved image to %s", filepath)
