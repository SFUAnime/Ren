#!/usr/bin/env python3

from contextlib import nullcontext as doesNotRaise
from datetime import datetime
import locale
from typing import ContextManager

locale.setlocale(locale.LC_ALL, ("en", "UTF-8"))

import pytest

from redbot.core import commands
from .converters import MonthDayConverter


@pytest.mark.asyncio
class TestMonthDayConverter:
    converter = MonthDayConverter()
    raiseNothing = doesNotRaise()
    raiseBadArgument = pytest.raises(commands.BadArgument)

    @pytest.mark.parametrize(
        ["dateString", "expectM", "expectD", "ctxMgr", "excString"],
        [
            ("2 3", 2, 3, raiseNothing, None),
            ("2 03", 2, 3, raiseNothing, None),
            ("02 3", 2, 3, raiseNothing, None),
            ("02 03", 2, 3, raiseNothing, None),
            ("29 Feb", 2, 29, raiseNothing, None),
            ("29 February", 2, 29, raiseNothing, None),
            ("Feb 29", 2, 29, raiseNothing, None),
            ("February 29", 2, 29, raiseNothing, None),
            ("some random text", None, None, raiseBadArgument, "Invalid date!"),
            ("February 30", None, None, raiseBadArgument, "Invalid date!"),
            (
                "February 29 00:01",
                None,
                None,
                raiseBadArgument,
                "Time information should not be supplied!",
            ),
        ],
    )
    async def testInputs(
        self, dateString: str, expectM: int, expectD: int, ctxMgr: ContextManager, excString: str
    ):
        with ctxMgr as excInfo:
            bday = await self.converter.convert(None, dateString)
            if excString:
                assert excString in str(excInfo.value)
            else:
                assert bday.month == expectM
                assert bday.day == expectD


locale.resetlocale(locale.LC_ALL)
