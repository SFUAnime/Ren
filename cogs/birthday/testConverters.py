#!/usr/bin/env python3

import dataclasses
from typing import Optional, Union
from unittest import mock

import pytest

from redbot.core import commands
from redbot.core.commands.context import Context

from .converters import MonthDayConverter


class TestMonthDayConverter:
    @dataclasses.dataclass
    class Case:
        dateStr: str
        expectedMonth: Optional[int]
        expectedDay: Optional[int]

    goodCases = (
        Case(dateStr="2 3", expectedMonth=2, expectedDay=3),
        Case(dateStr="2 03", expectedMonth=2, expectedDay=3),
        Case(dateStr="02 3", expectedMonth=2, expectedDay=3),
        Case(dateStr="02 03", expectedMonth=2, expectedDay=3),
        Case(dateStr="29 Feb", expectedMonth=2, expectedDay=29),
        Case(dateStr="29 February", expectedMonth=2, expectedDay=29),
        Case(dateStr="Feb 29", expectedMonth=2, expectedDay=29),
        Case(dateStr="February 29", expectedMonth=2, expectedDay=29),
    )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", goodCases)
    async def testGood(self, mockContext: Union[mock.Mock, Context], case: Case):
        actual = await MonthDayConverter().convert(ctx=mockContext, dateString=case.dateStr)
        assert actual.month == case.expectedMonth
        assert actual.day == case.expectedDay

    @dataclasses.dataclass
    class BadCase(Case):
        excStr: str

    badCases = (
        BadCase(
            dateStr="some random text",
            expectedMonth=None,
            expectedDay=None,
            excStr="Invalid date!",
        ),
        BadCase(
            dateStr="February 30",
            expectedMonth=None,
            expectedDay=None,
            excStr="Invalid date!",
        ),
        BadCase(
            dateStr="February 29 00:01",
            expectedMonth=None,
            expectedDay=None,
            excStr="Time information should not be supplied!",
        ),
    )

    @pytest.mark.parametrize("case", badCases)
    async def testBad(self, mockContext: Union[mock.Mock, Context], case: BadCase):
        with pytest.raises(commands.BadArgument) as excInfo:
            await MonthDayConverter().convert(mockContext, case.dateStr)
            assert case.excStr in str(excInfo.value)
