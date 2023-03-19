from typing import Union
from unittest import mock

import pytest

from redbot.core.commands.context import Context

from .heartbeat import Heartbeat
from .constants import KEY_INSTANCE_NAME, KEY_INTERVAL, KEY_PUSH_URL, MIN_INTERVAL


def contentFromMockContextSend(ctxSend: mock.Mock):
    """The value of the `content` argument of `ctxSend`.

    The provided `ctxSend` should be a mock object resembling
    `redbot.core.commands.context.Context.send`.
    """

    return ctxSend.call_args.kwargs.get("content") or ctxSend.call_args.args[0]


@pytest.mark.asyncio
async def testCmdCheck(cogHeartbeat: Heartbeat, mockContext: Union[mock.Mock, Context]):
    """Test to ensure `cmdCheck` works as expected."""

    instanceName = "test instance"
    await cogHeartbeat.cmdName(ctx=mockContext, name=instanceName)
    await cogHeartbeat.cmdCheck(ctx=mockContext)

    expectedReply = f"**{instanceName}** is responding."
    assert contentFromMockContextSend(ctxSend=mockContext.send) == expectedReply


@pytest.mark.asyncio
async def testCmdUrl(cogHeartbeat: Heartbeat, mockContext: Union[mock.Mock, Context]):
    """Test to ensure `cmdUrl` works as expected."""

    expectedUrl = "test url"
    await cogHeartbeat.cmdUrl(ctx=mockContext, url=expectedUrl)
    actualUrl = await cogHeartbeat.config.get_attr(KEY_PUSH_URL)()
    assert actualUrl == expectedUrl

    expectedReply = f"Set the push URL to: `{expectedUrl}`"
    assert contentFromMockContextSend(ctxSend=mockContext.send) == expectedReply


@pytest.mark.asyncio
@pytest.mark.parametrize(argnames="testInterval", argvalues=(MIN_INTERVAL, MIN_INTERVAL + 39))
async def testCmdIntervalGood(
    cogHeartbeat: Heartbeat,
    mockContext: Union[mock.Mock, Context],
    testInterval: int,
):
    """Test to ensure `cmdInterval` works as expected with good cases."""

    expectedInterval = testInterval
    await cogHeartbeat.cmdInterval(ctx=mockContext, interval=testInterval)
    actualInterval = await cogHeartbeat.config.get_attr(KEY_INTERVAL)()
    assert actualInterval == expectedInterval

    expectedReply = f"Set interval to: `{expectedInterval}` seconds"
    assert contentFromMockContextSend(ctxSend=mockContext.send) == expectedReply


@pytest.mark.asyncio
@pytest.mark.parametrize(argnames="testInterval", argvalues=(-1, MIN_INTERVAL - 1))
async def testCmdIntervalBad(
    cogHeartbeat: Heartbeat,
    mockContext: Union[mock.Mock, Context],
    testInterval: int,
):
    """Test to ensure `cmdInterval` works as expected with bad cases."""

    expectedInterval = await cogHeartbeat.config.get_attr(KEY_INTERVAL)()
    await cogHeartbeat.cmdInterval(ctx=mockContext, interval=testInterval)
    actualInterval = await cogHeartbeat.config.get_attr(KEY_INTERVAL)()
    assert actualInterval == expectedInterval

    expectedReply = f"Please set an interval greater than **{MIN_INTERVAL}** seconds"
    assert contentFromMockContextSend(ctxSend=mockContext.send) == expectedReply


@pytest.mark.asyncio
async def testCmdName(cogHeartbeat: Heartbeat, mockContext: Union[mock.Mock, Context]):
    """Test to ensure `cmdName` works as expected."""

    expectedName = "test instance name"
    await cogHeartbeat.cmdName(ctx=mockContext, name=expectedName)
    actualName = await cogHeartbeat.config.get_attr(KEY_INSTANCE_NAME)()
    assert actualName == expectedName

    expectedReply = f"Set the instance name to: `{expectedName}`"
    assert contentFromMockContextSend(ctxSend=mockContext.send) == expectedReply
