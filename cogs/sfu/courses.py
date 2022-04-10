"""This handles course lookups."""
import discord
from redbot.core import commands
from redbot.core.commands.context import Context
from .api import dictOutline
from .base import SFUBase


class SFUCourses(SFUBase):
    """A cog to search for SFU courses, from the kind souls at SFU CSSS."""

    # Class constructor
    def __init__(self, bot):
        super().__init__(bot)

        # Add commands to the sfu group defined in the base class
        self.sfuGroup.add_command(self.course)

    @commands.command()
    @commands.guild_only()
    async def course(
        self,
        ctx: Context,
        department: str,
        number: str,
        semester: str = None,
        year: str = None,
        section: str = None,
    ):
        """Display a course outline. Defaults to current semester and year.

        Parameters
        ----------
        department: str
            The course department. For example: engineering science = ensc
        number: str
            The course number. For example: 452
        semester: str (Optional)
            The semester for the course. Should be one of the following: spring, summer, fall
        year: str (Optional)
            The year of the course. For example: 2018

        For example, to find out about ENSC 452 in Spring 2018, use the following parameters:
        ensc 452 spring 2018
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
