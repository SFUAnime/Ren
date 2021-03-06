"""This handles course lookups."""
import discord
from redbot.core import commands
from redbot.core.commands.context import Context
from .api import dictOutline


class SFUCourses(commands.Cog):
    """A cog to search for SFU courses, from the kind souls at SFU CSSS."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="course")
    @commands.guild_only()
    async def lookup(
        self,
        ctx: Context,
        department: str,
        number: str,
        semester: str = None,
        year: str = None,
        section: str = None,
    ):
        """Displays a course outline.  Defaults to current semester and year.

        Semester: spring, summer, fall

        Original command from the SFU Computing Science Student Society.
        """
        if not section:
            section = "placeholder"
        if not year:
            year = "current"
        if not semester or semester.lower() not in ["fall", "summer", "spring"]:
            # self.logger.debug("Invalid semester")
            semester = "current"

        message = await ctx.send(":hourglass: Searching...")
        try:
            result = await dictOutline(department, number, section, year, semester)
        except ValueError:
            await message.edit(
                content=":warning: This course could not be found! "
                "Please retry with different parameters."
            )
            return

        embed = discord.Embed(title=result["Title"])

        valClassTimes = result["Class Times"]
        valExamTime = result["Exam Time"]
        if not valClassTimes:
            valClassTimes = "TBD"
        if not valExamTime:
            valExamTime = "TBD"

        # print(result)
        embed.add_field(name="Description", inline=False, value=result["Description"])
        embed.add_field(
            name="Details",
            inline=False,
            value="{} [More Info](https://www.sfu.ca/outlines."
            "html?{})".format(result["Details"], result["Outline"].lower()),
        )
        if result["Prerequisites"]:
            embed.add_field(name="Prerequisites", inline=False, value=result["Prerequisites"])
        embed.add_field(name="Instructor", value=result["Instructor"], inline=False)
        embed.add_field(name="Class Times", value=valClassTimes)
        embed.add_field(name="Exam Time", value=valExamTime)
        await message.edit(
            content=":information_source: Here is the course outline "
            "you requested, {}!".format(ctx.message.author.mention),
            embed=embed,
        )
