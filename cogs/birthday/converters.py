
from datetime import datetime
from redbot.core import commands

# Using February 29 or February 3 below, but %b, %B will be in the bot's
# locale.
# %Y in all cases will be a leap year (2020), omitting from examples
FORMAT_TUPLE: tuple = (
    "%m %d %Y", # 2 29, 02 29, 02 03, 2 3, etc.
    "%b %d %Y", # Feb 29, Feb 03, Feb 3
    "%d %b %Y", # 29 Feb, 03 Feb, 3 Feb
    "%B %d %Y", # February 29, February 3, February 03
    "%d %B %Y", # 29 February, 3 February, 03 February
)

class MonthDayConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, dateString: str) -> datetime: 
        inputDate = f"{dateString} 2020"
        for formatString in FORMAT_TUPLE:
            try:
                dateObj: datetime = datetime.strptime(inputDate, formatString)
            except ValueError:
                print(f"Error {formatString}, {inputDate}")
            else:
                return dateObj
        raise commands.BadArgument() 


