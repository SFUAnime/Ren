import aiohttp
import asyncio  # Used for task loop.

from redbot.core import Config
from redbot.core.bot import Red

from .constants import *


class Core:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_global(**DEFAULT_GLOBAL)
        self.bgTask = self.bot.loop.create_task(self._loop())

    async def _loop(self):
        session = aiohttp.ClientSession()
        initialInterval = await self.config.get_attr(KEY_INTERVAL)()
        LOGGER.info("Heartbeat is running, pinging at %s second intervals", initialInterval)

        countFailedPings = 0
        # the following loop shall break only on cancel event
        # and shall keep running on other exceptions until exceeding
        # the threshold for failed retries
        while self == self.bot.get_cog("Heartbeat"):
            try:
                await asyncio.sleep(await self.config.get_attr(KEY_INTERVAL)())
                url = await self.config.get_attr(KEY_PUSH_URL)()
                if url:
                    LOGGER.debug("Pinging %s", url)
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            # reset failed count to zero on success
                            LOGGER.debug("Successfully pinged %s", url)
                            countFailedPings = 0
                        else:
                            # increment failed count
                            LOGGER.error("HTTP GET failed! We got HTTP code %s", resp.status)
                            countFailedPings += 1
            except asyncio.CancelledError:
                # cancelled
                LOGGER.error(
                    "The background task got cancelled! If the cog was reloaded, "
                    "this can be safely ignored",
                    exc_info=True,
                )
                break
            except Exception:
                # keep retrying
                LOGGER.error("Something went wrong!", exc_info=True)
                countFailedPings += 1
            except:
                # these abnormal exceptions should not happen
                LOGGER.error("Something went horribly wrong!", exc_info=True)
                break

            if countFailedPings > 0:
                if countFailedPings <= MAX_FAILED_PINGS:
                    LOGGER.debug(
                        "Retrying in %d seconds... (attempt %d of %d)",
                        await self.config.get_attr(KEY_INTERVAL)(),
                        countFailedPings,
                        MAX_FAILED_PINGS,
                    )
                else:
                    LOGGER.error(
                        "Heartbeat main loop stopped after exceeding %d failed attempts",
                        MAX_FAILED_PINGS,
                    )
                    break

        # the session has to be closed
        if not session.closed:
            await session.close()

    # Cancel the background task on cog unload.
    def __unload(self):  # pylint: disable=invalid-name
        LOGGER.info("Cancelling heartbeat")
        self.bgTask.cancel()

    def cog_unload(self):
        self.__unload()
