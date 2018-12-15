# Imported code from Brendan Chan.
# https://github.com/brenfan/sfu-api/blob/master/python/courses.py
# Changes made by Injabie3.
# - Made it async to avoid blocking calls.
# - Changed some try, except blocks to if, else blocks.
import json
import aiohttp
import html
import re
from datetime import date

#Module for handling queries to the SFU Course Outlines API.
#API URL: http://www.sfu.ca/bin/wcm/course-outlines

#fetches data and returns a listionary
async def get_outline(dept, num, sec, year = 'current', term = 'current'):
    #setup params
    params = "?{0}/{1}/{2}/{3}/{4}".format(year, term, dept, num, sec)
    # Modified to be asynchronous.
    async with aiohttp.ClientSession() as session:
        async with session.get("http://www.sfu.ca/bin/wcm/course-outlines" + params) as resp:
            data = await resp.json()
    return data

#fetches sections and returns a dictionary
async def get_sections(dept, num, year = 'current', term = 'current'):
    #setup params
    params = "?{0}/{1}/{2}/{3}/".format(year, term, dept, num)
    # Modified to be asynchronous.
    async with aiohttp.ClientSession() as session:
        async with session.get("http://www.sfu.ca/bin/wcm/course-outlines" + params) as resp:
            data = await resp.json()
    return data

#returns a string containing the first section number with "LEC" as the sectionCode
async def find_section(dept, num, year = 'current', term = 'current'):
    #fetch data
    data = await get_sections(dept, num, year, term)
    try:
        for sec in data:
            if sec['sectionCode'] == "LEC" or sec['sectionCode'] == "LAB":
                return sec['value']
    except Exception:
        return None

#returns a course outline JSON Dictionary
async def find_outline(dept, num, sec='placeholder', year = 'current', term = 'current'):
    if sec == 'placeholder':
        sec = await find_section(dept, num, year, term)
        if sec == None:
            return None

    #print("sec = "  + sec)
    data = await get_outline(dept, num, sec, year, term)
    return data

#pulls data from outline JSON Dict
def extract(data:dict):
    #data aliases
    try:
        info = data['info']

        schedule = data['courseSchedule']

    except Exception:
        return ["Error: Maybe the class doesn't exist? \nreturned data:\n" + json.dumps(data)]

    #set up variable strings
    outlinepath = "{}".format(info['outlinePath'].upper())
    courseTitle = "{} ({} Units)".format(info['title'], info['units'])
    prof = ""
    try:
        for i in data['instructor']:
            prof += "{} ({})\n".format(i['name'], i['email'])
    except Exception:
        prof = "Unknown"

    classtimes = ""
    for time in schedule:
        classtimes += "[{}] {} {} - {}, {} {}, {}\n".format(
            time['sectionCode'],
            time['days'],
            time['startTime'],
            time['endTime'],
            time['buildingCode'],
            time['roomNumber'],
            time['campus'])
    examtime = ""
    try:
        for time in data['examSchedule']:
            if time['isExam']:
                examtime += "{} {} - {}\n{} {}, {}\n".format(
                    time['startDate'].split(" 00", 1)[0],
                    time['startTime'],
                    time['endTime'],
                    time['buildingCode'],
                    time['roomNumber'],
                    time['campus'])
    except Exception:
        #TBA I guess
        examtime = "TBA\n"
    description = info['description']
    try:
        details = info['courseDetails']
        #fix html entities
        details = html.unescape(details)
        #fix html tags
        details = re.sub('<[^<]+?>', '', details)
        #truncate
        limit = 500
        details = (details[:limit] + " ...") if len(details) > limit else details

    except Exception:
        details = ""
    
    if "prerequisites" in info.keys():
        prereq = info['prerequisites']
    else:
        prereq = ""

    if "corequisites" in info.keys():
        coreq = info['corequisites']
    else:
        coreq = ""

    return [outlinepath, courseTitle, prof, classtimes, examtime, description, details, prereq, coreq]

#formats the outline JSON into readable string
def format_outline(data:dict):
    strings= extract(data)

    if len(strings) == 1:
        return strings[0]

    outlinepath, courseTitle, prof, classtimes, examtime, description, details, prereq, coreq = strings
    #setup final formatting
    doc = ""
    doc += "Outline for: {}\n".format(outlinepath)
    doc += "Course Title: {}\n".format(courseTitle)
    doc += "Instructor: {}\n".format(prof)
    if classtimes != "":
        doc += "Class Times:\n{}\n".format(classtimes)
    doc += "Exam Time:\n{}\n".format(examtime)

    doc += "Description:\n{}\n\n".format(description)
    if details != "":
        doc += "Details:\n{}\n\n".format(details)
    if prereq != "":
        doc += "Prerequisites: {}\n".format(prereq)
    if coreq != "":
        doc += "Corequisites: {}\n".format(prereq)

    return doc

#returns a fairly nicely formatted string for easy reading
def print_outline(dept, num, sec='placeholder', year = 'current', term = 'current'):
    data = find_outline(dept, num, sec, year, term)
    return format_outline(data)

#returns a dictionary with relevant information
async def dict_outline(dept, num, sec='placeholder', year = 'current', term = 'current'):
    data = await find_outline(dept, num, sec, year, term)
    #print(data)
    strings = extract(data)
    #print(strings)
    if len(strings) == 1:
        raise ValueError({'Error': strings[0]})

    ret = {
        'Outline': strings[0],
        'Title': strings[1],
        'Instructor': strings[2],
        'Class Times':strings[3],
        'Exam Time':strings[4],
        'Description':strings[5],
        'Details':strings[6],
        'Prerequisites':strings[7],
        'Corequisites':strings[8]
    }
    return ret

#eturns two lists with relevant information
def list_outline(dept, num, sec='placeholder', year = 'current', term = 'current'):
    data = find_outline(dept, num, sec, year, term)
    #print(data)
    strings = extract(data)
    #print(strings)
    if len(strings) == 1:
        return ['Error'], strings
    #if

    keys =[
        'Outline',
        'Title',
        'Instructor',
        'Class Times',
        'Exam Time',
        'Description',
        'Details',
        'Prerequisites',
        'Corequisites'
    ]
    return keys, strings


##########################
import discord
from .utils.paginator import Pages # For making pages, requires the util!
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
from threading import Lock

class SFUCourses:
    """A cog to search for SFU courses, from the kind souls """
    # Class constructor
    def __init__(self, bot):
        self.bot = bot
            
    @commands.command(name="course", pass_context=True, no_pm=True)
    async def _courselookup(self, ctx, department: str, number: str, semester: str=None, year: str=None, section: str=None):
        """Displays a course outline.  Defaults to current semester and year.
        
        Semester: spring, summer, fall
        
        Original command from the SFU Computing Science Student Society.
        """
        if section is None:
            section = 'placeholder'
        if year is None:
            year = 'current'
        if semester is None or semester.lower() not in {"fall", "summer", "spring"}:
            # await self.bot.say("Debug: Invalid semester")
            semester = 'current'
            
        message = await self.bot.say(":hourglass: Searching...")
        try:
            result = await dict_outline(department, number, section, year, semester)
        except ValueError as e:
            await self.bot.edit_message(message, ":warning: This course could not be found!  Please retry with different parameters.")
            return
        except Exception as e:
            await self.bot.edit_message(message, ":warning:An error occurred while looking up the course.  Please try again.")
            print(e)
            return
        
        
        embed = discord.Embed(title="{0}".format(result["Title"]))
        # print(result)
        embed.add_field(name="Description", value=result["Description"])
        embed.add_field(name="Details", value=result["Details"]+"[More Info](https://www.sfu.ca/outlines.html?{})".format(result["Outline"].lower()))
        if result["Prerequisites"] != "":
            embed.add_field(name="Prerequisites", value=result["Prerequisites"])
        embed.add_field(name="Instructor", value=result["Instructor"], inline=False)
        embed.add_field(name="Class Times", value=result["Class Times"])
        embed.add_field(name="Exam Time", value=result["Exam Time"])
        await self.bot.edit_message(message, ":information_source: Here is the course outline you requested, {}!".format(ctx.message.author.mention))
        await self.bot.edit_message(message, embed=embed)
        
def setup(bot):
    cog = SFUCourses(bot)
    bot.add_cog(cog)
