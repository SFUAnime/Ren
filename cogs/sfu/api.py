"""API for SFU course information.

Imported code from Brendan Chan.
https://github.com/brenfan/sfu-api/blob/master/python/courses.py
Changes made by Injabie3.
- Made it async to avoid blocking calls.
- Changed some try, except blocks to if, else blocks.
"""
import json
import html
import re
import aiohttp


# Module for handling queries to the SFU Course Outlines API.
# API URL: http://www.sfu.ca/bin/wcm/course-outlines
async def getOutline(dept, num, sec, year="current", term="current"):
    """Get course outline.

    Below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    sec: str
        Section number. In the example, the section number is D100.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    dict
        A dictionary containing the relevant data about the course.
    """

    # setup params
    params = "?{0}/{1}/{2}/{3}/{4}".format(year, term, dept, num, sec)
    # Modified to be asynchronous.
    async with aiohttp.ClientSession() as session:
        async with session.get("http://www.sfu.ca/bin/wcm/course-outlines" + params) as resp:
            data = await resp.json()
    return data


# fetches sections and returns a dictionary
async def getSections(dept, num, year="current", term="current"):
    """Fetches the sections for a particular course.

    Below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    dict
        A dictionary containing dictionaries of the sections in the course.
    """
    # setup params
    params = "?{0}/{1}/{2}/{3}/".format(year, term, dept, num)
    # Modified to be asynchronous.
    async with aiohttp.ClientSession() as session:
        async with session.get("http://www.sfu.ca/bin/wcm/course-outlines" + params) as resp:
            data = await resp.json()
    return data


# returns a string containing the first section number with "LEC" as the sectionCode
async def findSection(dept, num, year="current", term="current"):
    """Returns the section for a particular course.

    Below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    str or None.
        A string containing the section number, or None if not found.
    """
    # fetch data
    data = await getSections(dept, num, year, term)
    try:
        for sec in data:
            if sec["sectionCode"] == "LEC" or sec["sectionCode"] == "LAB":
                return sec["value"]
    except (KeyError, TypeError):
        return None


# returns a course outline JSON Dictionary
async def findOutline(dept, num, sec="placeholder", year="current", term="current"):
    """Finds a course outline.

    Below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    sec: str
        Section number. In the example, this is D100.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    dict
        A dictionary containing the relevant data about the course.
    """
    if sec == "placeholder":
        sec = await findSection(dept, num, year, term)
        if not sec:
            return None

    # print("sec = "  + sec)
    data = await getOutline(dept, num, sec, year, term)
    return data


# pulls data from outline JSON Dict
def _extract(data: dict):
    # data aliases
    try:
        info = data["info"]

        schedule = data["courseSchedule"]

    except (KeyError, TypeError):
        return ["Error: Maybe the class doesn't exist? \nreturned data:\n" + json.dumps(data)]

    # set up variable strings
    outlinepath = "{}".format(info["outlinePath"].upper())
    courseTitle = "{} ({} Units)".format(info["title"], info["units"])
    prof = ""
    try:
        for i in data["instructor"]:
            prof += "{} ({})\n".format(i["name"], i["email"])
    except (KeyError, TypeError):
        prof = "Unknown"

    classtimes = ""
    for time in schedule:
        classtimes += "[{}] {} {} - {}, {} {}, {}\n".format(
            time["sectionCode"],
            time["days"],
            time["startTime"],
            time["endTime"],
            time["buildingCode"],
            time["roomNumber"],
            time["campus"],
        )
    examtime = ""
    try:
        for time in data["examSchedule"]:
            if time["isExam"]:
                examtime += "{} {} - {}\n{} {}, {}\n".format(
                    time["startDate"].split(" 00", 1)[0],
                    time["startTime"],
                    time["endTime"],
                    time["buildingCode"],
                    time["roomNumber"],
                    time["campus"],
                )
    except (KeyError, TypeError):
        # TBA I guess
        examtime = "TBA\n"
    description = info["description"]
    try:
        details = info["courseDetails"]
        # fix html entities
        details = html.unescape(details)
        # fix html tags
        details = re.sub("<[^<]+?>", "", details)
        # truncate
        limit = 500
        details = (details[:limit] + " ...") if len(details) > limit else details

    except (KeyError, TypeError):
        details = ""

    if "prerequisites" in info.keys():
        prereq = info["prerequisites"]
    else:
        prereq = ""

    if "corequisites" in info.keys():
        coreq = info["corequisites"]
    else:
        coreq = ""

    return [
        outlinepath,
        courseTitle,
        prof,
        classtimes,
        examtime,
        description,
        details,
        prereq,
        coreq,
    ]


def formatOutline(data: dict):
    """Formats the outline JSON into a readable string."""
    strings = _extract(data)

    if len(strings) == 1:
        return strings[0]

    (
        outlinepath,
        courseTitle,
        prof,
        classtimes,
        examtime,
        description,
        details,
        prereq,
        coreq,
    ) = strings
    # setup final formatting
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


def printOutline(dept, num, sec="placeholder", year="current", term="current"):
    """Returns a fiarly nicely formatted string for easy reading."""
    data = findOutline(dept, num, sec, year, term)
    return formatOutline(data)


# returns a dictionary with relevant information
async def dictOutline(dept, num, sec="placeholder", year="current", term="current"):
    """Searches the SFU calendar for a course.

    In the below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    sec: str
        Section number. In the example, the section number is D100.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    dict
        A dictionary containing the following keys (with their values):
        - Outline
        - Title
        - Instructor
        - Class Times
        - Exam Time
        - Description
        - Details
        - Prerequisites
        - Corequisites

    Raises:
    -------
    ValueError
        The course is invalid.
    """
    data = await findOutline(dept, num, sec, year, term)
    # print(data)
    strings = _extract(data)
    # print(strings)
    if len(strings) == 1:
        raise ValueError({"Error": strings[0]})

    ret = {
        "Outline": strings[0],
        "Title": strings[1],
        "Instructor": strings[2],
        "Class Times": strings[3],
        "Exam Time": strings[4],
        "Description": strings[5],
        "Details": strings[6],
        "Prerequisites": strings[7],
        "Corequisites": strings[8],
    }
    return ret


# eturns two lists with relevant information
def listOutline(dept, num, sec="placeholder", year="current", term="current"):
    """Searches the SFU calendar for a course.

    Below, assume the course is ENSC 452 D100 in Spring 2019.

    Parameters:
    -----------
    dept: str
        Department. In the example, the department is ENSC.
    num: str
        Course number. In the example, the course number is 452.
    sec: str
        Section number. In the example, the section number is D100.
    year: str
        Year: In the example, the year is 2019.
    term: str
        Term. One of the following strings (case-insensitive):
        - Spring
        - Summer
        - Fall
        In the example, the term is Spring.

    Returns:
    --------
    key, values: [ str ]
        Two lists: First, a list containing the following keys, and then another
        list with their corresponding values in the same position:
        - Outline
        - Title
        - Instructor
        - Class Times
        - Exam Time
        - Description
        - Details
        - Prerequisites
        - Corequisites

    Raises:
    -------
    ValueError
        The course was not found.
    """
    data = findOutline(dept, num, sec, year, term)
    # print(data)
    strings = _extract(data)
    # print(strings)
    if len(strings) == 1:
        raise ValueError({"Error": strings[0]})

    keys = [
        "Outline",
        "Title",
        "Instructor",
        "Class Times",
        "Exam Time",
        "Description",
        "Details",
        "Prerequisites",
        "Corequisites",
    ]
    return keys, strings
