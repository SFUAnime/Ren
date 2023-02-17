#!/usr/bin/env python3
import discord
import pytest


from .birthday import Birthday
from .constants import BOT_BIRTHDAY_MSG, CANNED_MESSAGES


class MockUser:
    def __init__(self, _id: int, mention: str):
        self.id = _id
        self.mention = mention


class MockBot:
    user = MockUser(1234, "Ren")


# XXX Move this out later once we refactor birthday cog layout
class TestBirthdayHelpers:
    bot = MockBot()

    @pytest.mark.parametrize(
        ["uid", "mention"],
        [
            (1111, "Onii-chan"),
            (2222, "Ara-ara Onee-chan"),
            (3333, "SENPAI"),
            (4444, "Sensei"),
        ],
    )
    def testGetBirthdayMessageWhenUserIsNotBot(self, mocker, uid, mention):
        # Do not initialize config, logger, and background task
        mocker.patch("birthday.Birthday.initializeConfigAndLogger")
        mocker.patch("birthday.Birthday.initializeBgTask")

        birthday = Birthday(self.bot)
        mockUser = MockUser(uid, mention)
        expectedMessages = [msg.format(mockUser.mention) for msg in CANNED_MESSAGES]

        msg = birthday.getBirthdayMessage(mockUser)
        assert msg in expectedMessages

    def testGetBirthdayMessageWhenUserIsBot(self, mocker):
        # Do not initialize config, logger, and background task
        mocker.patch("birthday.Birthday.initializeConfigAndLogger")
        mocker.patch("birthday.Birthday.initializeBgTask")

        birthday = Birthday(self.bot)
        mockUser = MockUser(1234, "Ren")

        msg = birthday.getBirthdayMessage(mockUser)
        assert msg == BOT_BIRTHDAY_MSG
