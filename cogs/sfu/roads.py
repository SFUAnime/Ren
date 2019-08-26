"""SFU Utilities.

- Web cameras: see road conditions in realtime.
- Campus report: fetched from the Road Report API.
"""
from io import BytesIO
import datetime
import json
import requests
from bs4 import BeautifulSoup
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context

WEBCAM_GAGLARDI = (
    "http://ns-webcams.its.sfu.ca/public/images/gaglardi-current.jpg"
    "?nocache=0.8678792633247998&update=15000&timeout=1800000&offset=4")
WEBCAM_TRS = ("http://ns-webcams.its.sfu.ca/public/images/towers-current.jpg"
              "?nocache=0.9550930672504077&update=15000&timeout=1800000")
WEBCAM_TRN = ("http://ns-webcams.its.sfu.ca/public/images/towern-current.jpg"
              "?nocache=1&update=15000&timeout=1800000")
WEBCAM_UDN = ("http://ns-webcams.its.sfu.ca/public/images/udn-current.jpg"
              "?nocache=1&update=15000&timeout=1800000&offset=4")
WEBCAM_AQPOND = ("http://ns-webcams.its.sfu.ca/public/images/aqn-current.jpg"
                 "?nocache=1&update=15000&timeout=1800000")
WEBCAM_SUB = ("http://ns-webcams.its.sfu.ca/public/images/aqsw-current.jpg"
              "?nocache=0.3346598630889852&update=15000&timeout=1800000")
WEBCAM_TFF = ("http://ns-webcams.its.sfu.ca/public/images/terryfox-current.jpg"
              "?nocache=1&update=15000&timeout=1800000")
ROAD_API = "http://www.sfu.ca/security/sfuroadconditions/api/3/current"

CAMPUSES = "campuses"
BUR = "burnaby"
SUR = "surrey"
VAN = "vancouver"
ROADS = "roads"
STATUS = "status"
ANNOUNCE = "announcements"


class SFURoads(commands.Cog):  # pylint: disable=too-few-public-methods
    """Various SFU Utilities."""
    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command(name="cam")
    @commands.guild_only()
    async def cam(self, ctx: Context, cam: str = ""):
        """SFU webcam, defaults to Gaglardi.

        Parameters:
        -----------
        cam: str
            One of the following short strings:
            aqpond: AQ Pond
            sub:    AQ overlooking student union building
            tff:    Terry Fox Field
            trn:    Tower Road North
            trs:    Tower Road South
            udn:    University Drive North
        """
        await ctx.trigger_typing()

        # We need a custom header or else we get a HTTP 403 Unauthorized
        headers = {"User-agent": "Mozilla/5.0"}

        try:
            if cam.lower() == "aqpond":
                fetchedData = requests.get(WEBCAM_AQPOND, headers=headers)
            elif cam.lower() == "help":
                await self.bot.send_help_for(ctx, self.cam)
                return
            elif cam.lower() == "sub":
                fetchedData = requests.get(WEBCAM_SUB, headers=headers)
            elif cam.lower() == "tff":
                fetchedData = requests.get(WEBCAM_TFF, headers=headers)
            elif cam.lower() == "trn":
                fetchedData = requests.get(WEBCAM_TRN, headers=headers)
            elif cam.lower() == "trs":
                fetchedData = requests.get(WEBCAM_TRS, headers=headers)
            elif cam.lower() == "udn":
                fetchedData = requests.get(WEBCAM_UDN, headers=headers)
            else:
                fetchedData = requests.get(WEBCAM_GAGLARDI, headers=headers)
            fetchedData.raise_for_status()
        except requests.exceptions.HTTPError:
            await ctx.send(":warning: This webcam is currently unavailable!")
            # self.logger.error(exc_info=True)
            return

        if not fetchedData.content:
            # Make sure we don't fetch a zero byte file
            await ctx.send(":warning: This webcam is currently unavailable!")
            return

        camPhoto = discord.File(BytesIO(fetchedData.content),
                                filename="cam.jpg")
        await ctx.send(file=camPhoto)

    @commands.command(name="report")
    @commands.guild_only()
    async def report(self, ctx: Context):
        """Show the SFU Campus Report."""
        fetchedData = requests.get(ROAD_API)
        results = json.loads(fetchedData.content)

        embed = discord.Embed()
        embed.title = "SFU Campus Report"

        # We need to use BeautifulSoup to parse the HTML within the JSON.
        if results[CAMPUSES][BUR][ANNOUNCE]:
            announce = BeautifulSoup(results[CAMPUSES][BUR][ANNOUNCE],
                                     "html.parser").get_text()
            roads = results[CAMPUSES][BUR][ROADS][STATUS]
            burnAnnounce = ("**__Roads__**:\n{}\n\n**__Announcements__**:"
                            "\n{}".format(roads, announce))
        else:
            burnAnnounce = "No updates."

        if results[CAMPUSES][SUR][ANNOUNCE]:
            surreyAnnounce = BeautifulSoup(results[CAMPUSES][SUR][ANNOUNCE],
                                           "html.parser").get_text()
        else:
            surreyAnnounce = "No updates."

        if results[CAMPUSES][VAN][ANNOUNCE]:
            vanAnnounce = BeautifulSoup(results[CAMPUSES][VAN][ANNOUNCE],
                                        "html.parser").get_text()
        else:
            vanAnnounce = "No updates."

        embed.add_field(name="Burnaby", value=burnAnnounce)
        embed.add_field(name="Vancouver", value=vanAnnounce)
        embed.add_field(name="Surrey", value=surreyAnnounce)

        lastUpdated = datetime.datetime.fromtimestamp(
            results["lastUpdated"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
        embed.set_footer(
            text="This report was last updated on {}".format(lastUpdated))
        await ctx.send(embed=embed)
