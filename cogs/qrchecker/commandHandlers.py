from typing import Optional

from redbot.core import commands
from redbot.core.commands import Context

from .commandsCore import CommandsCore


class CommandHandlers(CommandsCore):
    @commands.group(name="qrchecker")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _grpQrChecker(self, ctx: Context):
        """Configure QR code checker"""

    @_grpQrChecker.command(name="toggle")
    async def _cmdQrCheckerToggle(self, ctx: Context):
        """Toggle QR code checking"""
        await self.cmdQrCheckerToggle(ctx=ctx)

    @_grpQrChecker.command("show")
    async def _cmdQrCheckerShow(self, ctx: Context):
        """Show current settings"""
        await self.cmdQrCheckerShow(ctx=ctx)

    @_grpQrChecker.command(name="maxpixels")
    async def _cmdQrCheckerMaxPixels(self, ctx: Context, *, pixels: Optional[int]):
        """Set the maximum image pixels to check.

        Binary images are loaded into RAM in Pillow, which uses RAM. If your bot is
        running on a system with limited RAM, set this to a low value to avoid OOM
        killer from killing your bot.

        Parameters
        ----------
        pixels: Optional[int]
            The maximum number of pixels in an image to check.
        """
        await self.cmdQrCheckerMaxPixels(ctx=ctx, pixels=pixels)
