import asyncio
import unittest.mock

import pytest
import pytest_asyncio

from redbot.core.bot import Red
from redbot.core.commands.context import Context

from .core import Core
from .heartbeat import Heartbeat


@pytest_asyncio.fixture()
async def cogHeartbeat(
    monkeypatch: pytest.MonkeyPatch,
    red: Red,
    event_loop: asyncio.AbstractEventLoop,
):
    """A fixture of `Heartbeat` loaded by a Red instance.
    Note that the background loop of the cog provided by this fixture will not run upon cog instantiation."""

    red.loop = event_loop

    try:
        with monkeypatch.context() as patchContext:
            # In test environments, we intentionally disable
            # the background task of the cog to avoid the
            # coroutine being unexpectedly terminated when
            # the test session completes. If the background
            # task needs to be tested, then method _loop
            # can be examined accordingly.
            patchContext.setattr(target=Core, name="_loop", value=unittest.mock.AsyncMock())
            await red.add_cog(Heartbeat(bot=red))

        cog = red.get_cog(Heartbeat.__name__)
        assert isinstance(cog, Heartbeat)

        cog.bgTask.cancel()

        yield cog

    finally:
        await red.remove_cog(Heartbeat.__name__)


@pytest.fixture()
def mockContext():
    return unittest.mock.create_autospec(spec=Context)
