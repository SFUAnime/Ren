import random
import typing

import pytest

from . import constants, helpers


class Utils:
    @classmethod
    def randomNumberString(cls, len: int, digits: str = "0123456789"):
        """Returns a string of specified length and of specified digits chosen randomly."""
        return "".join(random.choice(digits) for _ in range(len))

    @classmethod
    def insertStringIntoString(cls, str1: str, str2: str, pos: typing.Optional[int] = None):
        """Returns the result of inserting str1 into str2 at position pos.
        If pos is not specified, a random position in str2 will be chosen."""
        if pos is None:
            return Utils.insertStringIntoString(str1, str2, random.randint(0, len(str2)))
        return "".join((str2[:pos], str1, str2[pos:]))


class TestCheckLengthInRaw:
    """Tests to ensure helper checkLengthInRaw() works as expected."""

    # good cases
    @pytest.mark.parametrize(
        ["content"],
        map(
            lambda content: [content],
            (
                "",
                "**test**",
                "~~**__`test`__**~~",
                "~~**__```test```__**~~",
                Utils.randomNumberString(constants.MAX_MSG_LEN),
                Utils.insertStringIntoString(
                    "test",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 4),
                ),
                Utils.insertStringIntoString(
                    "**test**",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 12),
                ),
                Utils.insertStringIntoString(
                    "~~**__`test`__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 32),
                ),
                Utils.insertStringIntoString(
                    "~~**__`test`__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 64),
                ),
                Utils.insertStringIntoString(
                    "~~**__```test```__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 40),
                ),
                Utils.insertStringIntoString(
                    "~~**__```test```__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 64),
                ),
                # cases with non-effective block-quotes
                Utils.insertStringIntoString(
                    ">~~**__```test```__**~~<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 42),
                ),
                Utils.insertStringIntoString(
                    ">>>~~**__```test```__**~~<<<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 46),
                ),
                # cases with effective block-quotes
                Utils.insertStringIntoString(
                    "> ~~**__```test```__**~~ <",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 45),
                    0,  # single-line block-quotes are only effective preceded by nothing and followed by something
                ),
                Utils.insertStringIntoString(
                    ">>> ~~**__```test```__**~~ <<<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 49),
                    0,  # single-line block-quotes are only effective preceded by nothing and followed by something
                ),
                # cases with non-ASCII characters
                Utils.insertStringIntoString(
                    "~*_`ネコミミ大好き`_*~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 23),
                ),
                Utils.insertStringIntoString(
                    "~*_`ねこみみだいすき`_*~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 24),
                ),
                # cases with markdown-lookalike characters
                Utils.insertStringIntoString(
                    "‘＊＿~*_`バーバラ＊いっくよ！～`_*~＿＊‘",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 33),
                ),
                # cases with markdown effective block-quote lookalike characters
                Utils.insertStringIntoString(
                    "＞ ~*_`バーバラ＊いっくよ！～`_*~ ＜",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 31),
                    0,
                ),
                Utils.insertStringIntoString(
                    "＞＞＞ ~*_`バーバラ＊いっくよ！～`_*~ ＜＜＜",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 35),
                    0,
                ),
            ),
        ),
    )
    def testGoodCases(self, content: str):
        assert helpers.checkLengthInRaw(content)

    # bad cases
    @pytest.mark.parametrize(
        ["content"],
        map(
            lambda content: [content],
            (
                Utils.randomNumberString(constants.MAX_MSG_LEN * 2),
                Utils.randomNumberString(constants.MAX_MSG_LEN + 1),
                Utils.insertStringIntoString(
                    "**test**",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 8),
                ),
                Utils.insertStringIntoString(
                    "**test**",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 10),
                ),
                Utils.insertStringIntoString(
                    "**test**",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 11),
                ),
                Utils.insertStringIntoString(
                    "~~**__`test`__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 14),
                ),
                Utils.insertStringIntoString(
                    "~~**__`test`__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 31),
                ),
                Utils.insertStringIntoString(
                    "~~**__```test```__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 20),
                ),
                Utils.insertStringIntoString(
                    "~~**__```test```__**~~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 39),
                ),
                # cases with non-effective block-quotes
                Utils.insertStringIntoString(
                    ">~~**__```test```__**~~<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 41),
                ),
                Utils.insertStringIntoString(
                    ">>>~~**__```test```__**~~<<<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 45),
                ),
                # cases with effective block-quotes
                Utils.insertStringIntoString(
                    "> ~~**__```test```__**~~ <",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 44),
                    0,
                ),
                Utils.insertStringIntoString(
                    ">>> ~~**__```test```__**~~ <<<",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 48),
                    0,
                ),
                # cases with non-ASCII characters
                Utils.insertStringIntoString(
                    "~*_`ネコミミ大好き`_*~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 22),
                ),
                Utils.insertStringIntoString(
                    "~*_`ねこみみだいすき`_*~",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 23),
                ),
                # cases with markdown-lookalike characters
                Utils.insertStringIntoString(
                    "‘＊＿~*_`バーバラ＊いっくよ！～`_*~＿＊‘",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 32),
                ),
                # cases with markdown effective block-quote lookalike characters
                Utils.insertStringIntoString(
                    "＞ ~*_`バーバラ＊いっくよ！～`_*~ ＜",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 30),
                    0,
                ),
                Utils.insertStringIntoString(
                    "＞＞＞ ~*_`バーバラ＊いっくよ！～`_*~ ＜＜＜",
                    Utils.randomNumberString(constants.MAX_MSG_LEN - 34),
                    0,
                ),
            ),
        ),
    )
    def testBadCases(self, content: str):
        assert not helpers.checkLengthInRaw(content)
