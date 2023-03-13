import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Union
from unittest import mock

import aiohttp
import pytest
from pytest import LogCaptureFixture, MonkeyPatch

from redbot.core.bot import Red

from . import constants, core
from .heartbeat import Heartbeat


def createMockClientResponseGet(response: aiohttp.ClientResponse):
    @asynccontextmanager
    async def mockGet(*_args, **_kwargs):
        yield response

    return mockGet


@pytest.mark.asyncio
async def testLoopBad(caplog: LogCaptureFixture, monkeypatch: MonkeyPatch, red: Red):
    """Test to ensure `_loop` works as expected with bad case: the response from the push URL is always non-OK."""

    # prep
    red.loop = mock.create_autospec(spec=asyncio.AbstractEventLoop)
    minInterval = 1
    maxFailedPings = 3
    core.MAX_FAILED_PINGS = maxFailedPings

    # mock
    mockResponse: Union[mock.Mock, aiohttp.ClientResponse] = mock.create_autospec(
        spec=aiohttp.ClientResponse,
        status=500,  # i.e., HTTP 500
    )

    # patch
    monkeypatch.setattr(
        target=aiohttp.ClientSession,
        name="get",
        value=createMockClientResponseGet(response=mockResponse),
    )

    # log
    caplog.set_level(level=logging.ERROR)

    # cog
    await red.add_cog(Heartbeat(bot=red))
    cog: Heartbeat = red.get_cog("Heartbeat")
    assert cog and isinstance(cog, Heartbeat)

    # prep
    testInterval = minInterval
    await cog.config.get_attr(constants.KEY_INSTANCE_NAME).set("test instance")
    await cog.config.get_attr(constants.KEY_PUSH_URL).set("test URL")
    await cog.config.get_attr(constants.KEY_INTERVAL).set(testInterval)

    # test
    try:
        await asyncio.wait_for(cog._loop(), testInterval * core.MAX_FAILED_PINGS * 2)
    except asyncio.TimeoutError:
        pytest.fail(reason="The main loop should have failed, but is still running.")
    assert (
        caplog.records[-1].getMessage()
        == f"Heartbeat main loop stopped after exceeding {maxFailedPings} failed attempts"
    )

    await red.remove_cog("Heartbeat")
    assert cog.bgTask.done()
