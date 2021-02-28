from abc import ABC

from redbot.core import commands
from redbot.core.commands.context import Context

from .base import SFUBase
from .roads import SFURoads
from .courses import SFUCourses


class SFU(SFUCourses, SFURoads):
    """SFU resources on Discord."""
