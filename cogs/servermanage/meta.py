from abc import ABC
from redbot.core import commands


class ServerManageMeta(type(commands.Cog), type(ABC)):
    pass
