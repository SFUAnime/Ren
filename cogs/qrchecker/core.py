from logging import getLogger

from redbot.core import Config
from redbot.core.bot import Red

from .constants import BASE_GUILD


class Core:
    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = getLogger("red.luicogs.QRChecker")
        self.config = Config.get_conf(self, identifier=5842647, force_registration=True)
        self.config.register_guild(**BASE_GUILD)
