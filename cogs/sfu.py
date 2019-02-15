"""SFU web cameras
See road conditions in realtime.
"""

import os
import urllib.request
from discord.ext import commands

WEBCAM_GAGLARDI = ("http://ns-webcams.its.sfu.ca/public/images/gaglardi-current.jpg"
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
SAVE_FOLDER = "data/lui-cogs/webcam/" # Path to save folder.
SAVE_FILE = "settings.json"

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

class SFUCam: # pylint: disable=too-few-public-methods
    """SFU Webcams."""

    # Class constructor
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cam", pass_context=True)
    async def cam(self, ctx, cam: str = ""):
        """SFU webcam, defaults to Gaglardi.

        Parameters:
        -----------
        cam: str
            One of the following short strings:
            trs:    Tower Road South
            trn:    Tower Road North
            udn:    University Drive North
            aqpond: AQ Pond
            sub:    AQ overlooking student union building
        """
        await self.bot.send_typing(ctx.message.channel)
        path = "{}{}.jpg".format(SAVE_FOLDER, "webcam")
        opener = urllib.request.build_opener()
        # We need a custom header or else we get a HTTP 403 Unauthorized
        opener.addheaders = [("User-agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        try:
            if cam.lower() == "trs":
                urllib.request.urlretrieve(WEBCAM_TRS, path)
            elif cam.lower() == "trn":
                urllib.request.urlretrieve(WEBCAM_TRN, path)
            elif cam.lower() == "udn":
                urllib.request.urlretrieve(WEBCAM_UDN, path)
            elif cam.lower() == "aqpond":
                urllib.request.urlretrieve(WEBCAM_AQPOND, path)
            elif cam.lower() == "sub":
                urllib.request.urlretrieve(WEBCAM_SUB, path)
            else:
                urllib.request.urlretrieve(WEBCAM_GAGLARDI, path)
        except urllib.request.ContentTooShortError:
            return None
        except urllib.error.HTTPError:
            await self.bot.say(":warning: This webcam is currently unavailable!")
            return
        if os.stat(path).st_size == 0:
            await self.bot.say(":warning: This webcam is currently unavailable!")
            return

        await self.bot.send_file(ctx.message.channel, path)


def setup(bot):
    """Add the cog to the bot."""
    checkFolder()
    customCog = SFUCam(bot)
    bot.add_cog(customCog)
