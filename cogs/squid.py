# imports to make the dream

import random
import asyncio
import discord
import commands

''' dab '''
class dab:
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = "squid", pass_context = True)
    async def mycom(self):
	
        number = random.randint(0, 10000)
    
        # prints some ASCII art to whom ever is lucky enough
        if number == 420:
		
            await.self.bot.say("Squidward will visit you")
            await asyncio.sleep(5)
            await.self.bot.say("https://media3.giphy.com/media/lae7QSMFxEkkE/giphy.gif")
            await asyncio.sleep(5)
            await.self.bot.say("Squidward has visited you")
        
      
        # for the unlucky ones
        else:
            await.self.bot.say("He won't visit you yet")
            await.self.bot.say("Maybe if you're lucky you'll get to see him")
        
      
      
