"""QR Code Checker

Requires:
- pyzbar from PyPI
- libzbar0 from your distro's package repo
"""
from io import BytesIO
from typing import Dict, List, Optional
from logging import Logger, getLogger

from discord import AllowedMentions, Guild, Message
from pyzbar.pyzbar import Decoded, decode, ZBarSymbol
from PIL import Image
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.config import Group
from redbot.core.utils.chat_formatting import box, pagify

KEY_ENABLED: str = "enabled"

BASE_GUILD: Dict = {KEY_ENABLED: False}


class QRChecker(commands.Cog):
    """A QR code checker for attachments"""

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.logger: Logger = getLogger("red.luicogs.QRChecker")
        self.config: Config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)

    @commands.Cog.listener("on_message")
    async def listener(self, message: Message):
        """Find QR code in message attachments"""
        if not message.guild:
            return
        # check if enabled
        if not await self.config.guild(message.guild).get_attr(KEY_ENABLED)():
            self.logger.debug(
                "QR Checker disabled for %s (%s); return early",
                message.guild.name,
                message.guild.id,
            )
            return
        if not message.attachments:
            self.logger.debug("No attachments, return early")
            return
        for attachment in message.attachments:
            contentType: Optional[str] = attachment.content_type
            if not contentType:
                self.logger.debug("Unknown content type, continue")
                continue
            elif contentType and "image" not in contentType:
                self.logger.debug("Not an image, continue")
                continue

            # At this point we decern that it's an image.
            try:
                fp: BytesIO = BytesIO(await attachment.read())
                image: Image = Image.open(fp)
                codes: List[Decoded] = decode(image, symbols=[ZBarSymbol.QRCODE])
                self.logger.debug("Found %s codes", len(codes))
            except Exception:
                self.logger.error("Couldn't check file.", exc_info=True)
                return

            if not codes:
                self.logger.debug("No QR codes found.")
                return

            self.logger.info(
                "%s#%s (%s) posted some QR code(s) in #%s (%s)",
                message.author.name,
                message.author.discriminator,
                message.author.id,
                message.channel.name,
                message.channel.id,
            )

            numQrCodes = len(codes)
            if numQrCodes == 1:
                code: Decoded = codes[0]
                data: str = code.data.decode()
                if len(data) == 0:
                    self.logger.debug("No data in QR code.")
                    return
                if len(data) > 1900:
                    contents: str = f"{data[:1900]}..."
                else:
                    contents: str = data
                msg = (
                    f"Found a QR code from {message.author.mention}, "
                    f"the contents are: {box(contents)}"
                )
                await message.reply(
                    msg, mention_author=False, allowed_mentions=AllowedMentions.none()
                )
            else:
                hasData: bool = False
                pages: List[str] = []
                pages.append(
                    f"Found several QR codes from {message.author.mention}, their contents are:"
                )
                for code in codes:
                    data: str = code.data.decode()
                    if len(data) == 0:
                        self.logger.debug("No data in QR code.")
                        continue
                    if len(data) > 1990:
                        contents: str = f"{box(data[:1990])}..."
                    else:
                        contents: str = f"{box(data)}"
                    pages.append(contents)
                    hasData |= True

                if not hasData:
                    self.logger.debug("No data in %s QR codes.", numQrCodes)
                    return

                firstMessage: bool = True
                sentMessages: int = 0

                ctx: Context = await self.bot.get_context(message)
                for textToSend in pagify("\n".join(pages), escape_mass_mentions=True):
                    if firstMessage:
                        await message.reply(
                            textToSend,
                            mention_author=False,
                            allowed_mentions=AllowedMentions.none(),
                        )
                        firstMessage = False
                    elif sentMessages > 10:
                        self.logger.debug("Sent more than 10 messages, bail early")
                        break
                    else:
                        await ctx.send(textToSend, allowed_mentions=AllowedMentions.none())
                    sentMessages += 1

    @commands.group(name="qrchecker")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def qrchecker(self, ctx: Context):
        """Configure QR code checker"""
        pass

    # toggle command
    @qrchecker.command(name="toggle")
    async def qrcheckerToggle(self, ctx: Context):
        """Toggle QR code checking"""
        guild: Guild = ctx.guild
        if not guild:
            return
        guildConfig: Group = self.config.guild(guild)

        enabled: bool = await guildConfig.get_attr(KEY_ENABLED)()
        if enabled:
            await guildConfig.get_attr(KEY_ENABLED).set(False)
            await ctx.send("QR code checking is now **disabled** for this guild.")
        else:
            await guildConfig.get_attr(KEY_ENABLED).set(True)
            await ctx.send("QR code checking is now **enabled** for this guild.")
