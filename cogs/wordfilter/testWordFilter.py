import re

import pytest

from .wordfilter import (
    _filterWord,
    _isAllFiltered,
    _isOneWord,
)


class TestHelperFunctions:
    @pytest.mark.parametrize(
        ["inputPhrase", "toFilter", "result"],
        [
            ("I am cool", "am", "I `**` cool"),
            (
                "https://discord.gg/testing123",
                r"(discord.gg\/)(?!YcW3AtX)(?!MmpqtqD)[a-zA-Z0-9]*",
                "https://`*********************`",
            ),
            (
                "https://discord.gg/YcW3AtX",
                r"(discord.gg\/)(?!YcW3AtX)(?!MmpqtqD)[A-Za-z0-9,]*",
                "https://discord.gg/YcW3AtX",
            ),
        ],
    )
    def testFilterWordSingle(self, inputPhrase, toFilter, result):
        filteredPhrase = _filterWord([toFilter], inputPhrase)
        assert result == filteredPhrase

    @pytest.mark.parametrize("inputPhrase", ["https://discord.gg/testing123"])
    def testFilterWordNoRegexFilter(self, inputPhrase):
        filteredPhrase = _filterWord([], inputPhrase)
        assert filteredPhrase == inputPhrase

    @pytest.mark.parametrize(
        ["inputStr", "result"],
        [
            ("test", True),
            ("another phrase", False),
        ],
    )
    def testIsOneWord(self, inputStr, result):
        assert _isOneWord(inputStr) == result

    @pytest.mark.parametrize(
        ["inputStr", "result"],
        [
            ("test", False),
            ("***** phrase", False),
            ("**** **another** **phrase**", False),
            ("F*CKING B*LLSH*T", False),
            ("* ** ***", True),
            (" *** **** ", True),
            ("**** ** ****", True),
        ],
    )
    def testIsAllFiltered(self, inputStr, result):
        assert _isAllFiltered(inputStr) == result
