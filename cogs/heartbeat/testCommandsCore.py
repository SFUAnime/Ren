import asyncio
from typing import Union
from unittest import mock

import pytest

from redbot.core.bot import Red
from redbot.core.commands.context import Context

from .heartbeat import Heartbeat
from .constants import KEY_INSTANCE_NAME, KEY_INTERVAL, KEY_PUSH_URL, MIN_INTERVAL


@pytest.mark.asyncio
async def testCmdCheck(red: Red):
    """Test to ensure `cmdCheck` works as expected."""

    # prep
    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    cog = Heartbeat(bot=red)
    ctx: Union[mock.Mock, Context] = mock.create_autospec(spec=Context)
    ctxSend: mock.Mock = ctx.send
    # test
    instanceName = "test instance"
    await cog.cmdName(ctx=ctx, name=instanceName)
    await cog.cmdCheck(ctx=ctx)
    expectedReply = f"**{instanceName}** is responding."
    actualReply = ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]
    assert actualReply == expectedReply


@pytest.mark.asyncio
async def testCmdUrl(red: Red):
    """Test to ensure `cmdUrl` works as expected."""

    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    cog = Heartbeat(bot=red)
    ctx: Union[mock.Mock, Context] = mock.create_autospec(spec=Context)
    ctxSend: mock.Mock = ctx.send
    expectedUrl = "test url"
    await cog.cmdUrl(ctx=ctx, url=expectedUrl)
    actualUrl = await cog.config.get_attr(KEY_PUSH_URL)()
    assert actualUrl == expectedUrl
    expectedReply = f"Set the push URL to: `{expectedUrl}`"
    actualReply = ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]
    assert actualReply == expectedReply


@pytest.mark.asyncio
@pytest.mark.parametrize(argnames="testInterval", argvalues=(MIN_INTERVAL, MIN_INTERVAL + 39))
async def testCmdIntervalGood(red: Red, testInterval: int):
    """Test to ensure `cmdInterval` works as expected with good cases."""

    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    cog = Heartbeat(bot=red)
    ctx: Union[mock.Mock, Context] = mock.create_autospec(spec=Context)
    ctxSend: mock.Mock = ctx.send
    expectedInterval = testInterval
    await cog.cmdInterval(ctx=ctx, interval=testInterval)
    actualInterval = await cog.config.get_attr(KEY_INTERVAL)()
    assert actualInterval == expectedInterval
    expectedReply = f"Set interval to: `{expectedInterval}` seconds"
    actualReply = ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]
    assert actualReply == expectedReply


@pytest.mark.asyncio
@pytest.mark.parametrize(argnames="testInterval", argvalues=(-1, MIN_INTERVAL - 1))
async def testCmdIntervalBad(red: Red, testInterval: int):
    """Test to ensure `cmdInterval` works as expected with bad cases."""

    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    cog = Heartbeat(bot=red)
    ctx: Union[mock.Mock, Context] = mock.create_autospec(spec=Context)
    ctxSend: mock.Mock = ctx.send
    expectedInterval = await cog.config.get_attr(KEY_INTERVAL)()
    await cog.cmdInterval(ctx=ctx, interval=testInterval)
    actualInterval = await cog.config.get_attr(KEY_INTERVAL)()
    assert actualInterval == expectedInterval
    expectedReply = f"Please set an interval greater than **{MIN_INTERVAL}** seconds"
    actualReply = ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]
    assert actualReply == expectedReply


@pytest.mark.asyncio
async def testCmdName(red: Red):
    """Test to ensure `cmdName` works as expected."""

    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    cog = Heartbeat(bot=red)
    ctx: Union[mock.Mock, Context] = mock.create_autospec(spec=Context)
    ctxSend: mock.Mock = ctx.send
    expectedName = "test instance name"
    await cog.cmdName(ctx=ctx, name=expectedName)
    actualName = await cog.config.get_attr(KEY_INSTANCE_NAME)()
    assert actualName == expectedName
    expectedReply = f"Set the instance name to: `{expectedName}`"
    actualReply = ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]
    assert actualReply == expectedReply
