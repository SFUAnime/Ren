from io import BytesIO
from typing import List

from discord import AllowedMentions, Message
from PIL import Image
from pyzbar.pyzbar import Decoded, decode, ZBarSymbol

from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import box, pagify

from .constants import KEY_ENABLED
from .core import Core


class EventsCore(Core):
    async def evtListener(self, message: Message):
        """Find QR code in message attachments"""
        if not self.initialized:
            return

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
            contentType = attachment.content_type
            if not contentType:
                self.logger.debug("Unknown content type, continue")
                continue
            elif contentType and "image" not in contentType:
                self.logger.debug("Not an image, continue")
                continue

            # At this point we decern that it's an image.
            async with self.lock:
                try:
                    fp: BytesIO = BytesIO(await attachment.read())
                    image: Image = Image.open(fp)
                    codes: List[Decoded] = decode(image, symbols=[ZBarSymbol.QRCODE])
                    self.logger.debug("Found %s codes", len(codes))
                except Image.DecompressionBombError as error:
                    self.logger.error("Couldn't check file, image too large: %s", error)
                    return
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
                code = codes[0]
                data: str = code.data.decode()
                if len(data) == 0:
                    self.logger.debug("No data in QR code.")
                    return
                if len(data) > 1900:
                    contents = f"{data[:1900]}..."
                else:
                    contents = data
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
                        contents = f"{box(data[:1990])}..."
                    else:
                        contents = f"{box(data)}"
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
