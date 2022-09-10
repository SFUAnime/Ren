#!/usr/bin/env python3

from datetime import datetime
import locale

locale.setlocale(locale.LC_ALL, ("en", "UTF-8"))

import pytest

from redbot.core import commands
from .converters import MonthDayConverter


@pytest.mark.asyncio
class TestMonthDayConverter:
    converter = MonthDayConverter()

    @staticmethod
    def verifyFeb29(bday: datetime):
        assert bday.month == 2
        assert bday.day == 29

    @staticmethod
    def verifyFeb3(bday: datetime):
        assert bday.month == 2
        assert bday.day == 3

    @pytest.mark.parametrize("dateString", ("29 Feb", "29 February"))
    async def testDayTextMonth(self, dateString):
        bday = await self.converter.convert(None, dateString)
        self.verifyFeb29(bday)

    @pytest.mark.parametrize("inputString", ("February 30", "some random text"))
    async def testInvalidDate(self, inputString):
        with pytest.raises(commands.BadArgument) as excInfo:
            await self.converter.convert(None, inputString)
        assert "Invalid date!" in str(excInfo.value)

    async def testTime(self):
        with pytest.raises(commands.BadArgument) as excInfo:
            await self.converter.convert(None, "February 29 00:01")
        assert "Time information should not be supplied!" in str(excInfo.value)

    @pytest.mark.parametrize("dateString", ("02 03", "02 3", "2 03", "2 3"))
    async def testNumMonthDay(self, dateString):
        bday = await self.converter.convert(None, dateString)
        self.verifyFeb3(bday)

    @pytest.mark.parametrize("dateString", ("February 29", "Feb 29"))
    async def testTextMonthDay(self, dateString):
        bday = await self.converter.convert(None, dateString)
        self.verifyFeb29(bday)


locale.resetlocale(locale.LC_ALL)
