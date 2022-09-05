#!/usr/bin/env python3

from datetime import datetime
import locale

locale.setlocale(locale.LC_ALL, ("en", "UTF-8") )

import pytest
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

    async def testNumMonthDay(self):
        bday = await self.converter.convert(None, "02 03")
        self.verifyFeb3(bday)

        bday = await self.converter.convert(None, "02 3")
        self.verifyFeb3(bday)

        bday = await self.converter.convert(None, "2 03")
        self.verifyFeb3(bday)

        bday = await self.converter.convert(None, "2 3")
        self.verifyFeb3(bday)

    async def testLongMonthDay(self):
        bday = await self.converter.convert(None, "February 29")
        self.verifyFeb29(bday)

    async def testShortMonthDay(self):
        bday = await self.converter.convert(None, "Feb 29")
        self.verifyFeb29(bday)

locale.resetlocale(locale.LC_ALL)
