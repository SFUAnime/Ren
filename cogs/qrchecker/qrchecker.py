"""QR Code Checker

Requires:
- pyzbar from PyPI
- libzbar0 from your distro's package repo
"""

from redbot.core import commands

from .commandHandlers import CommandHandlers
from .eventHandlers import EventHandlers


class QRChecker(commands.Cog, CommandHandlers, EventHandlers):
    """A QR code checker for attachments"""
