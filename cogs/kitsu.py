import requests

import discord
from discord.ext import commands

import html
import re

class Kitsu:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True)
    async def kitsu(self, ctx):
        """ Commands to get anime/manga information from kitsu """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @kitsu.command(pass_context=True)
    async def anime(self, ctx):
        """ Find anime on Kitsu by given name
        
        **Example**:
        ~kitsu anime Toradora!
        
        """
        name = ctx.message.content.split(" ")[1:]
        if not name:
            return await self.bot.say("No anime specified")
        
        url = 'https://kitsu.io/api/edge/anime'
        params = {'filter[text]': name}
        
        with requests.get(url, params=params) as resp:
            resp = resp.json()['data']
            if not resp:
                return await self.bot.say("Anime not found")

        anime = resp[0]
 
        synopsis = html.unescape(anime['attributes']['synopsis'])
        synopsis = re.sub(r'<.*?>', '', synopsis)
        synopsis = synopsis.replace('[Written by MAL Rewrite]', '')
        synopsis = synopsis[0:425] + '...'
        url = 'https://kitsu.io/anime/{anime["id"]}'

        genreurl = anime['relationships']['genres']['links']['related']
        genres = []
        with requests.get(genreurl) as resp:
            for item in resp.json()['data']:
                genres.append(item['attributes']['name'])

        genres = ", ".join(genres)

        await self.bot.say(embed=discord.Embed(
            colour=discord.Colour.red(), 
            url=url
        ).set_thumbnail(
             url=anime['attributes']['posterImage']['small']
        ).set_author(
            name=anime['attributes']['titles']['en_jp'],
            icon_url=anime['attributes']['posterImage']['small']
        ).add_field(
            name='Community approval',
            value=anime['attributes']['averageRating']
        ).add_field(
            name='Episodes',
            value=anime['attributes']['episodeCount']
        ).add_field(
            name='Status',
            value=anime['attributes']['status']
        ).add_field(
            name='Type',
            value=anime['attributes']['showType']
        ).add_field(
            name='Genres',
            value=genres
        ).add_field(
            name="Description",
            value=synopsis
        ).set_footer(
            text='\u200b',
            icon_url='https://pbs.twimg.com/profile_images/807964865511862278/pIYOVdsl.jpg'
        ))

    @kitsu.command(pass_context=True)
    async def manga(self, ctx):
        """ Find manga on kitsu by given name
        
        **Example**:
        ~kitsu manga Sakurasou no pet na Kanojo
        
        """
        name = ctx.message.content.split(" ")[1:]
        if not name:
            return await self.bot.say("No manga specified")

        
        url = 'https://kitsu.io/api/edge/manga'
        params = {'filter[text]': name}
        
        with requests.get(url, params=params) as resp:
            resp = resp.json()['data']
            if not resp:
                return await self.bot.say("Manga not found")

        manga = resp[0]

        synopsis = html.unescape(manga['attributes']['synopsis'])
        synopsis = re.sub(r'<.*?>', '', synopsis)
        synopsis = synopsis.replace('[Written by MAL Rewrite]', '')
        synopsis = synopsis[0:425] + '...'
        url = 'https://kitsu.io/manga/{manga["id"]}'

        genreurl = manga['relationships']['genres']['links']['related']
        genres = []
        with requests.get(genreurl) as resp:
            for item in resp.json()['data']:
                genres.append(item['attributes']['name'])

        genres = ", ".join(genres)

        await self.bot.say(embed=discord.Embed(
            colour=discord.Colour.red(), 
            url=url
        ).set_thumbnail(
             url=manga['attributes']['posterImage']['small']
        ).set_author(
            name=manga['attributes']['titles']['en_jp'],
            icon_url=manga['attributes']['posterImage']['small']
        ).add_field(
            name='Community approval',
            value=manga['attributes']['averageRating']
        ).add_field(
            name='Chapters',
            value=manga['attributes']['chapterCount']
        ).add_field(
            name='Status',
            value=manga['attributes']['status']
        ).add_field(
            name='Type',
            value=manga['type']
        ).add_field(
            name='Genres',
            value=genres
        ).add_field(
            name="Description",
            value=synopsis
        ).set_footer(
            text='\u200b',
            icon_url='https://pbs.twimg.com/profile_images/807964865511862278/pIYOVdsl.jpg'
        ))

    

def setup(bot):
    bot.add_cog(Kitsu(bot))
