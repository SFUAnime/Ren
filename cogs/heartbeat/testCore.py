import asyncio
from contextlib import asynccontextmanager
from http import HTTPStatus
import logging
from typing import Union
from unittest import mock

import aiohttp
import pytest
from pytest import LogCaptureFixture, MonkeyPatch

from . import constants, core
from .heartbeat import Heartbeat


def createMockClientResponseGet(response: aiohttp.ClientResponse):
    @asynccontextmanager
    async def mockGet(*_args, **_kwargs):
        yield response

    return mockGet


@pytest.mark.asyncio
async def testLoopBad(
    caplog: LogCaptureFixture,
    monkeypatch: MonkeyPatch,
    event_loop: asyncio.AbstractEventLoop,
    cogHeartbeat: Heartbeat,
):
    """Test to ensure `_loop` works as expected with bad case in which the response from the push URL is always non-OK."""

    # prep
    minInterval = 1
    maxFailedPings = 3
    testInterval = minInterval
    core.MAX_FAILED_PINGS = maxFailedPings

    # mock
    mockResponse: Union[mock.Mock, aiohttp.ClientResponse] = mock.create_autospec(
        spec=aiohttp.ClientResponse,
        status=int(HTTPStatus.INTERNAL_SERVER_ERROR),
    )

    # patch
    monkeypatch.setattr(
        target=aiohttp.ClientSession,
        name="get",
        value=createMockClientResponseGet(response=mockResponse),
    )

    # config
    await cogHeartbeat.config.get_attr(constants.KEY_INSTANCE_NAME).set("test instance")
    await cogHeartbeat.config.get_attr(constants.KEY_PUSH_URL).set("test URL")
    await cogHeartbeat.config.get_attr(constants.KEY_INTERVAL).set(testInterval)

    # log
    caplog.clear()
    caplog.set_level(level=logging.ERROR)

    # mock + patch asyncio.sleep:
    # we do not care about whether the realtime sleep duration has been as expected,
    # but rather the fact that the loop should have done asyncio.sleep maxFailedPings
    # times, and should stop due to maxFailedPings fails.
    mockSleep = mock.AsyncMock()
    monkeypatch.setattr(target=asyncio, name="sleep", value=mockSleep)

    # test
    try:
        await asyncio.wait_for(
            fut=event_loop.create_task(coro=cogHeartbeat._loop()),
            timeout=testInterval * maxFailedPings * 2,
        )
    except asyncio.TimeoutError:
        pytest.fail(reason="The main loop should have failed, but is still running.")

    assert (
        mockSleep.await_count == maxFailedPings + 1
    )  # plus 1 because the loop sleeps before checking failed ping count

    for call_args in mockSleep.call_args_list:
        sleepDuration = call_args.kwargs.get("delay") or call_args.args[0]
        assert sleepDuration == testInterval

    assert (
        caplog.records[-1].getMessage()
        == f"Heartbeat main loop stopped after exceeding {maxFailedPings} failed attempts"
    )
