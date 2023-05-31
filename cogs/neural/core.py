import os
from asyncio import Lock, sleep
from collections import deque
from datetime import datetime, timedelta
from logging import FileHandler, Formatter, Logger, getLogger
from pathlib import Path
from random import random
from typing import Deque, Dict, List, Optional

from discord import Message, TextChannel
from langchain.llms import OpenAI

from redbot.core import Config, data_manager
from redbot.core.bot import Red

from .constants import (
    BASE_CHANNEL,
    BASE_TYPING_WAIT,
    CHAT_HISTORY_CHAR_LIMIT,
    FOLLOW_UP_CHANCE,
    INBOUND_BUFFER_CHAR_LIMIT,
    INIT_CHAT_HISTORY_LIMIT,
    KEY_BASE_FOLLOW_UP,
    KEY_LONG_MESSAGE_FOLLOW_UP,
    KEY_QUESTION_FOLLOW_UP,
    LLM_API_BASE,
    LLM_API_KEY,
    LLM_API_PRESENCE_PENALTY,
    LONG_MESSAGE_CUTOFF,
    OLD_CHAT_HISTORY_CHAR_LIMIT,
    STALE_CHAT_PERIOD,
    SYSTEM_MESSAGE_STR,
)
from .prompts import chatPrompt, chatPromptBotName, chatReversePrompt
from .utils import isProbablyCommand


class Core:
    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.inboundBufferLock: Lock = Lock()
        self.chatLock: Lock = Lock()
        self.config: Config = Config.get_conf(
            self,
            identifier=5842647,
            force_registration=True,
        )
        self.config.register_channel(**BASE_CHANNEL)
        # Initialize logger and save to cog folder
        saveFolder: Path = data_manager.cog_data_path(cog_instance=self)
        self.logger: Logger = getLogger("red.luicogs.Neural")
        if not self.logger.handlers:
            logPath: str = os.path.join(saveFolder, "info.log")
            handler: FileHandler = FileHandler(
                filename=logPath,
                encoding="utf-8",
                mode="a",
            )
            handler.setFormatter(
                Formatter("%(asctime)s %(message)s", datefmt="[%Y/%m/%d %H:%M:%S]")
            )
            self.logger.addHandler(handler)
        # Initialize vars that track chat state
        self.chatChannelId: Optional[int] = None
        # Channel ID, data
        self.inboundBuffer: Dict[int, Deque[Message]] = {}  # TODO: class
        self.chatHistory: Dict[int, Deque[str]] = {}
        self.lastTypingTime: Dict[int, datetime] = {}
        self.lastReplyTime: Dict[int, datetime] = {}

    async def initChannelChatState(self, channel: TextChannel) -> None:
        """Initialize the chat state on `channel`."""
        self.chatChannelId = channel.id
        self.inboundBuffer[channel.id] = deque()
        messageHistory: List[Message] = [
            message async for message in channel.history(limit=INIT_CHAT_HISTORY_LIMIT)
        ]
        for message in reversed(messageHistory):
            if await self.filterInbound(message):
                await self.appendInboundBuffer(message)
        self.chatHistory[channel.id] = deque()
        self.updateLastTypingTime(channel.id)
        self.lastReplyTime[channel.id] = datetime.now()

    async def filterInbound(self, message: Message) -> bool:
        """Return whether `message` should be seen by the chat model."""
        if not isinstance(message.channel, TextChannel):
            return False
        if message.content.startswith(SYSTEM_MESSAGE_STR):
            return False
        if message.attachments:
            return False
        if await isProbablyCommand(self.bot, message):
            return False
        return True

    async def appendInboundBuffer(self, message: Message) -> None:
        """Append the message to its channel's inbound buffer."""
        async with self.inboundBufferLock:
            channelId: int = message.channel.id
            if channelId in self.inboundBuffer:
                self.inboundBuffer[channelId].append(message)
            else:
                self.inboundBuffer[channelId] = deque([message])
            # If necessary, delete older messages to keep buffer size under control
            bufferLengthChars: int = 0
            for msg in self.inboundBuffer[channelId]:
                bufferLengthChars += len(msg.content)
            while bufferLengthChars > INBOUND_BUFFER_CHAR_LIMIT:
                bufferLengthChars -= len(self.inboundBuffer[channelId][0].content)
                self.inboundBuffer[channelId].popleft()

    async def clearInboundBuffer(self, channel: TextChannel) -> None:
        """Clear the inbound buffer on `channel`."""
        async with self.inboundBufferLock:
            self.inboundBuffer[channel.id].clear()

    def updateLastTypingTime(self, channelId: int) -> None:
        """Update last typing timestamp for the channel."""
        self.lastTypingTime[channelId] = datetime.now()

    async def waitForTyping(self, channel: TextChannel) -> bool:
        """Wait for a while,
        then return whether someone had started typing on `channel` during the wait.
        """
        oldTypingTime: Optional[datetime] = self.lastTypingTime.get(channel.id)
        bufferLen: int = len(self.inboundBuffer[channel.id])
        # Don't wait too long if messages are piling up in the buffer
        waitSeconds: float = BASE_TYPING_WAIT / (bufferLen + 1) + random()
        await sleep(waitSeconds)
        newTypingTime: Optional[datetime] = self.lastTypingTime.get(channel.id)
        if oldTypingTime != newTypingTime:
            return True
        return False

    async def stepChat(self, channel: TextChannel) -> None:
        """Step the chat on `channel` forward by one reply cycle."""
        # Load then clear the inbound buffer
        inboundBufferSnapshot: Deque[Message] = self.inboundBuffer[channel.id].copy()
        await self.clearInboundBuffer(channel)
        # Load the incoming messages into chat history
        if not channel.id in self.chatHistory:
            self.chatHistory[channel.id] = deque()  # No chat history yet, make new
        for message in inboundBufferSnapshot:
            promptUsername: str = message.author.display_name
            if message.author.id == self.bot.user.id:
                promptUsername = chatPromptBotName
            # fmt: off
            formattedMessage: str = (
                f"{chatReversePrompt} {promptUsername}:\n"
                f"{message.content}\n"
                "\n"
            )
            # fmt: on
            self.chatHistory[channel.id].append(formattedMessage)
        # Join the chat history into a single string
        chatHistoryPrompt: str = "".join(self.chatHistory[channel.id])
        # Prepare the LLM query
        llm: OpenAI = OpenAI(
            openai_api_base=LLM_API_BASE,
            openai_api_key=LLM_API_KEY,
            presence_penalty=LLM_API_PRESENCE_PENALTY,
        )
        prompt: str = chatPrompt.format(
            channelName=channel.name,
            messageHistory=chatHistoryPrompt,
        )
        self.logger.info("\n======Passed to API:======\n%s", prompt)
        # Query the LLM
        async with channel.typing():
            response: str = await llm.apredict(
                text=prompt,
                stop=[chatReversePrompt],
            )
        await channel.send(response)
        # Update the chat history
        # fmt: off
        formattedResponse: str = (
            f"{chatReversePrompt} Ren:\n"
            f"{response}"
        )
        # fmt: on
        self.chatHistory[channel.id].append(formattedResponse)
        self.lastReplyTime[channel.id] = datetime.now()

    async def startChat(self, channel: TextChannel) -> None:
        """Start a chat on `channel`."""
        await self.stepChat(channel)

    async def continueChat(self, channel: TextChannel) -> None:
        """Continue the chat on `channel`."""
        await self.stepChat(channel)
        if channel.last_message.author.id == self.bot.user.id:
            followUpChance: float
            if "?" in channel.last_message.content:
                followUpChance = FOLLOW_UP_CHANCE[KEY_QUESTION_FOLLOW_UP]
            elif len(channel.last_message.content) > LONG_MESSAGE_CUTOFF:
                followUpChance = FOLLOW_UP_CHANCE[KEY_LONG_MESSAGE_FOLLOW_UP]
            else:
                followUpChance = FOLLOW_UP_CHANCE[KEY_BASE_FOLLOW_UP]
            if random() < followUpChance:
                await sleep(random())
                await self.continueChat(channel)

    def endChat(self, channel: TextChannel) -> None:
        """End the chat on `channel`. Keep a small portion of the chat history."""
        chatHistoryLengthChars: int = len("".join(self.chatHistory[channel.id]))
        while chatHistoryLengthChars > OLD_CHAT_HISTORY_CHAR_LIMIT:
            chatHistoryLengthChars -= len(self.chatHistory[channel.id][0])
            self.chatHistory[channel.id].popleft()

    def hasOversizedChat(self, channel: TextChannel) -> bool:
        """Return whether the chat history on `channel` is over the token limit."""
        chatHistoryLengthChars: int = len("".join(self.chatHistory[channel.id]))
        if chatHistoryLengthChars > CHAT_HISTORY_CHAR_LIMIT:
            return True
        return False

    def hasStaleChat(self, channel: TextChannel) -> bool:
        """Return whether there is a stale chat on `channel`."""
        timeSinceLastReply: timedelta = datetime.now() - self.lastReplyTime[channel.id]
        if timeSinceLastReply.total_seconds() > STALE_CHAT_PERIOD:
            return True
        return False
