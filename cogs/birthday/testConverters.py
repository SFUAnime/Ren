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

    async def testDayLongMonth(self):
        bday = await self.converter.convert(None, "29 February")
        self.verifyFeb29(bday)

    async def testDayShortMonth(self):
        bday = await self.converter.convert(None, "29 Feb")
        self.verifyFeb29(bday)

    async def testInvalidDate(self):
        inputTuple = ("February 30", "some random text")
        for inputString in inputTuple:
            with pytest.raises(commands.BadArgument) as excInfo:
                await self.converter.convert(None, inputString)
            assert "Invalid date!" in str(excInfo.value)

        with pytest.raises(commands.BadArgument) as excInfo:
            await self.converter.convert(None, "February 29 00:01")
        assert "Time information should not be supplied!" in str(excInfo.value)

    @pytest.mark.parametrize("dateString", ("02 03", "02 3", "2 03", "2 3"))
    async def testNumMonthDay(self, dateString):
        bday = await self.converter.convert(None, dateString)
        self.verifyFeb3(bday)

    async def testLongMonthDay(self):
        bday = await self.converter.convert(None, "February 29")
        self.verifyFeb29(bday)

    async def testShortMonthDay(self):
        bday = await self.converter.convert(None, "Feb 29")
        self.verifyFeb29(bday)


locale.resetlocale(locale.LC_ALL)
