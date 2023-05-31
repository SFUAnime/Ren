from random import random

from discord import Message, RawTypingEvent

from .constants import (
    CHAT_END_CHANCE,
    CHAT_START_CHANCE,
    KEY_AT_MENTION_START,
    KEY_CASUAL_MENTION_START,
    KEY_NEURAL_ACTIVE,
    KEY_SELF_END,
    KEY_SELF_START,
    KEY_STALE_CHAT_END,
    KEY_TOKEN_LIMIT_END,
)
from .core import Core
from .utils import isAtMention, isCasualMention


class EventsCore(Core):
    async def eventOnMessage(self, message: Message) -> None:
        """Decide when to start/continue/end a conversation."""
        if not await self.config.channel(message.channel).get_attr(KEY_NEURAL_ACTIVE)():
            return
        if message.author.id == self.bot.user.id:
            return
        if not await self.filterInbound(message):
            return
        # Put incoming messages in buffer to split them into batches
        await self.appendInboundBuffer(message)
        # Decide whether to defer to next batch
        if await self.waitForTyping(message.channel):
            return
        if self.chatLock.locked():
            return
        # Handle one batch at a time
        async with self.chatLock:
            # If not in a chat, decide whether to start one
            if self.chatChannelId is None:
                chatStartChance: float
                if isAtMention(self.bot.user.name, message):
                    chatStartChance = CHAT_START_CHANCE[KEY_AT_MENTION_START]
                elif isCasualMention(self.bot.user.display_name, message):
                    chatStartChance = CHAT_START_CHANCE[KEY_CASUAL_MENTION_START]
                else:
                    chatStartChance = CHAT_START_CHANCE[KEY_SELF_START]
                if random() < chatStartChance:
                    await self.startChat(message.channel)
                    self.chatChannelId = message.channel.id
            # If in a chat, and it's on this channel, decide whether to continue/end
            elif self.chatChannelId == message.channel.id:
                chatEndChance: float
                if self.hasOversizedChat(message.channel):
                    chatEndChance = CHAT_END_CHANCE[KEY_TOKEN_LIMIT_END]
                elif self.hasStaleChat(message.channel):
                    chatEndChance = CHAT_END_CHANCE[KEY_STALE_CHAT_END]
                else:
                    chatEndChance = CHAT_END_CHANCE[KEY_SELF_END]
                if random() > chatEndChance:
                    await self.continueChat(message.channel)
                else:
                    self.endChat(message.channel)
                    self.chatChannelId = None

    async def eventOnRawTyping(self, payload: RawTypingEvent) -> None:
        """Update a timestamp when someone starts typing on the chat channel."""
        if payload.channel_id == self.chatChannelId:
            self.updateLastTypingTime(payload.channel_id)
