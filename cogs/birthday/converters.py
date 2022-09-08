from datetime import datetime
from dateutil.parser import parse, ParserError
from redbot.core import commands

# Using default year of 2020 for a leap year.
DEFAULT_DATE: datetime = datetime(2020, 1, 1)


class MonthDayConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, dateString: str) -> datetime:
        try:
            dateObj = parse(dateString, default=DEFAULT_DATE)
        except ParserError:
            raise commands.BadArgument("Invalid date!")

        if any([dateObj.hour, dateObj.minute, dateObj.second, dateObj.microsecond]):
            raise commands.BadArgument("Time information should not be supplied!")

        return dateObj
