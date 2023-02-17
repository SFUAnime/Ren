from discord import Message

from redbot.core import commands

from .eventsCore import EventsCore


class EventHandlers(EventsCore):
    @commands.Cog.listener("on_message")
    async def _evtListener(self, message: Message):
        """Find QR code in message attachments"""
        await self.evtListener(message=message)
