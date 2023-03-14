import asyncio
import unittest.mock

import pytest

from redbot.core.bot import Red
from redbot.core.commands.context import Context

from .heartbeat import Heartbeat


@pytest.fixture()
async def cogHeartbeat(red: Red, event_loop: asyncio.AbstractEventLoop):
    """A fixture of `Heartbeat` loaded by a Red instance."""

    red.loop = event_loop

    try:
        await red.add_cog(Heartbeat(bot=red))
        cog = red.get_cog(Heartbeat.__name__)
        assert isinstance(cog, Heartbeat)

        # In test environments, we intentionally cancel
        # the background task of the cog to avoid the
        # coroutine being unexpectedly terminated when
        # the test session completes. If the background
        # task needs to be tested, then method _loop can
        # be examined accordingly.
        cog.bgTask.cancel()

        yield cog

    finally:
        await red.remove_cog(Heartbeat.__name__)


@pytest.fixture()
def mockContext():
    return unittest.mock.create_autospec(spec=Context)
