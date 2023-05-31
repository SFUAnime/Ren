from discord import Message, RawTypingEvent

from redbot.core import commands

from .eventsCore import EventsCore


class EventHandlers(EventsCore):
    @commands.Cog.listener("on_message")
    async def _eventOnMessage(self, message: Message) -> None:
        """Decide when to start/continue/end a conversation."""
        await self.eventOnMessage(message=message)

    @commands.Cog.listener("on_raw_typing")
    async def _eventOnRawTyping(self, payload: RawTypingEvent) -> None:
        """Update a timestamp when someone starts typing on the chat channel."""
        await self.eventOnRawTyping(payload=payload)
