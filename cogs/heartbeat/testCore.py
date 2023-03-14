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

    # test
    try:
        await asyncio.wait_for(
            fut=event_loop.create_task(coro=cogHeartbeat._loop()),
            timeout=testInterval * maxFailedPings * 2,
        )
    except asyncio.TimeoutError:
        pytest.fail(reason="The main loop should have failed, but is still running.")
    assert (
        caplog.records[-1].getMessage()
        == f"Heartbeat main loop stopped after exceeding {maxFailedPings} failed attempts"
    )
