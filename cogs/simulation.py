import random
import json
import typing

import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class Simulation(utils.Cog):

    BASE_URL = "https://api.weeb.sh"
    ALLOWED_REACTIONS = {
        "cry",
        "cuddle",
        "hug",
        "kiss",
        "pat",
        "slap",
        "tickle",
        "bite",
        "punch",
    }

    async def get_reaction_gif(self, reaction_type:str):
        """
        Pings the endpoint, gets a reaction gif, bish bash bosh.
        """

        # Make sure we can run this command
        if not self.bot.config.get('command_data', {}).get('weeb_sh_api_key'):
            self.logger.debug("No API key set for Weeb.sh")
            return None

        # Make sure we can use this input
        if reaction_type not in self.ALLOWED_REACTIONS:
            self.logger.debug(f"Invalid reaction {reaction_type} passed to get_reaction_gif")
            return None

        # Set up our params
        headers = {
            "User-Agent": self.bot.user_agent,
            "Authorization": f"Wolke {self.bot.config['command_data']['weeb_sh_api_key']}"
        }
        params = {
            "type": reaction_type,
            "nsfw": "false",
        }

        # Run request wew
        async with self.bot.session.get(f"{self.BASE_URL}/images/random", params=params, headers=headers) as r:
            try:
                data = await r.json()
            except Exception as e:
                data = await r.text()
                self.logger.warning(f"Error from Weeb.sh ({e}): {data}")
                return None
            if str(r.status)[0] == "2":
                return data['url']

        # Oh no it wasn't a good boy oh jeez oh heck
        self.logger.warning(f"Error from Weeb.sh: {data}")
        return None

    async def get_gif_url(self, guild_id:int, interaction_type:str) -> typing.Optional[str]:
        """
        Get the GIF URL for the given guild ID and interaction type.
        """

        async with self.bot.database() as db:
            rows = await db("SELECT gifs_enabled FROM guild_settings WHERE guild_id=ANY($1::BIGINT[]) ORDER BY guild_id DESC", [guild_id, 0])
        enabled = rows[0]['gifs_enabled']
        if enabled is False:
            return None
        return await self.get_reaction_gif(self.bot, interaction_type)

    @utils.command(aliases=['snuggle', 'cuddle'])
    @commands.bot_has_permissions(send_messages=True)
    async def hug(self, ctx:utils.Context, user:discord.Member):
        """Hugs a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You hug yourself... and start crying.*")
        await ctx.send(
            f"*Hugs {user.mention}*",
            image_url=await self.get_reaction_gif(ctx.guild.id, "hug"),
        )

    @utils.command(aliases=['smooch'])
    @commands.bot_has_permissions(send_messages=True)
    async def kiss(self, ctx:utils.Context, user:discord.Member):
        """Kisses a mentioned user"""

        if user == ctx.author:
            return await ctx.send("How would you even manage to do that?")
        await ctx.send(
            f"*{ctx.author.mention} leans up to {user.mention} and gives them a lil smooch.*",
            image_url=await self.get_reaction_gif(ctx.guild.id, "kiss"),
        )

    @utils.command(aliases=['smack'])
    @commands.bot_has_permissions(send_messages=True)
    async def slap(self, ctx:utils.Context, user:discord.Member):
        """Slaps a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You slapped yourself... for some reason.*")
        await ctx.send(
            f"*Slaps {user.mention}*",
            image_url=await self.get_reaction_gif(ctx.guild.id, "slap"),
        )

    @utils.command()
    @commands.bot_has_permissions(send_messages=True)
    async def coffee(self, ctx:utils.Context, user:discord.Member):
        """Gives coffee to a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You spilled coffee all over yourself... for some reason.*")
        await ctx.send(f"*Gives coffee to {user.mention}*")

    @utils.command()
    @commands.bot_has_permissions(send_messages=True)
    async def punch(self, ctx:utils.Context, user:discord.Member):
        """Punches a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You punched yourself... for some reason.*")
        await ctx.send(
            f"*Punches {user.mention} right in the nose*",
            image_url=await self.get_reaction_gif(ctx.guild.id, "punch"),
        )

    @utils.command(hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def cookie(self, ctx:utils.Context, user:discord.Member):
        """Gives a cookie to a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You gave yourself a cookie.*")
        await ctx.send(f"*Gives {user.mention} a cookie*")

    @utils.command(aliases=['borger', 'borg', 'burge'], hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def burger(self, ctx:utils.Context, user:discord.Member):
        """Gives a burger to a mentioned user"""

        if user == ctx.author:
            return await ctx.send(f"*You give yourself a {ctx.invoked_with}* 🍔")
        await ctx.send(f"*Gives {user.mention} a {ctx.invoked_with}* 🍔")

    @utils.command(hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def tea(self, ctx:utils.Context, user:discord.Member):
        """Gives tea to a mentioned user"""

        if user == ctx.author:
            return await ctx.send("*You gave yourself tea.*")
        await ctx.send(f"*Gives {user.mention} tea*")

    @utils.command(aliases=['dumpster'], hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def garbage(self, ctx:utils.Context, user:discord.Member):
        """Throws a user in the garbage"""

        if user == ctx.author:
            return await ctx.send("*You climb right into the trash can, where you belong*")
        await ctx.send(f"*Throws {user.mention} into the dumpster*")

    @utils.command(hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def poke(self, ctx:utils.Context, user:discord.Member):
        """Pokes a given user"""

        if user == ctx.author:
            return await ctx.send("You poke yourself.")
        await ctx.send(
            f"*Pokes {user.mention}.*",
            image_url=await self.get_reaction_gif(ctx.guild.id, "poke"),
        )

    @utils.command(hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def stab(self, ctx:utils.Context, user:discord.Member):
        """Stabs a mentioned user"""

        if user == ctx.author:
            responses = [
                "You stab yourself.",
                "Looks like you don't have a knife, oops!",
                "No.",
            ]
        else:
            responses = [
                f"You stab {user.mention}.",
                f"{user.mention} has been stabbed.",
                f"*stabs {user.mention}.*",
                "Looks like you don't have a knife, oops!",
                "You can't legally stab someone without thier consent.",
                "Stab? Isn't that, like, illegal?",
                "I wouldn't recommend doing that tbh.",
            ]
        await ctx.send(random.choice(responses))

    @utils.command(aliases=['murder'], hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def kill(self, ctx:utils.Context, user:discord.Member=None):
        """Kills a person :/"""

        responses = [
            "That would violate at least one of the laws of robotics.",
            "I am a text-based bot. I cannot kill.",
            "Unfortunately, murder isn't supported in this version of MarriageBot.",
            "Haha good joke there, but I'd never kill a person! >.>",
            "To my knowledge, you can't kill via the internet. Let me know when that changes.",
            "I am designed to bring people together, not murder them.",
        ]
        await ctx.send(random.choice(responses))

    @utils.command(aliases=['vore'], hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def eat(self, ctx:utils.Context, user:discord.Member):
        """Eats a person OwO"""

        responses = [
            f"You swallowed {user.mention}... through the wrong hole.",
            f"You've eaten {user.mention}. Gross.",
            f"Are you into this or something? You've eaten {user.mention}.",
            f"I guess lunch wasnt good enough. You eat {user.mention}.",
            f"You insert {user.mention} into your mouth and proceed to digest them.",
        ]
        await ctx.send(random.choice(responses))

    @utils.command(aliases=['intercourse', 'fuck', 'smash', 'heck'], hidden=True)
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True)
    async def copulate(self, ctx:utils.Context, user:discord.Member):
        """Lets you... um... heck someone"""

        # See if they want to marry
        result = await localutils.utils.send_proposal_message(
            ctx, user, f"Hey, {user.mention}; you wanna fuck {ctx.author.mention}?",
        )
        if result is None:
            return

        if result:
            responses = [
                f"{ctx.author.mention} and {user.mention} got frisky~",
                f"{ctx.author.mention} and {user.mention} spent some alone time together ~~wink wonk~~",
                f"{ctx.author.mention} and {user.mention} made sexy time together ;3",
                f"{ctx.author.mention} and {user.mention} attempted to make babies.",
                f"{ctx.author.mention} and {user.mention} tried to have relations but couldn't find the hole.",
                f"{ctx.author.mention} and {user.mention} went into the wrong hole.",
                f"{ctx.author.mention} and {user.mention} tried their hardest, but they came too early .-.",
                f"{ctx.author.mention} and {user.mention} slobbed each other's knobs.",
                f"{ctx.author.mention} and {user.mention} had some frisky time in the pool and your doodoo got stuck because of pressure.",
                f"{ctx.author.mention} and {user.mention} had sex and you've contracted an STI. uh oh!",
                f"{ctx.author.mention} and {user.mention} had sex but you finished early and now it's just a tad awkward.",
                f"Jesus saw what {ctx.author.mention} and {user.mention} did.",
                f"{ctx.author.mention} and {user.mention} did a lot of screaming.",
                f"{ctx.author.mention} and {user.mention} had sex and pulled a muscle. No more hanky panky for a while!",
                f"{ctx.author.mention} and {user.mention}... just please keep it down.",
                f"Wrap it before you tap it, {ctx.author.mention} and {user.mention}.",
                f"{ctx.author.mention} and {user.mention} did the thing with the thing... oh gosh. Ew.",
                f"Bing bong {ctx.author.mention}, turns out {user.mention} wants your ding dong!",
                f"{user.mention} and {ctx.author.mention} did the nasty while spanking each others bum cheeks!",
                f"{user.mention} and {ctx.author.mention} went to town, if you know what I mean.",
                f"{user.mention} and {ctx.author.mention} got it on. I sure hope Jesus consented, too...",
                f"{user.mention} and {ctx.author.mention} are getting freaky, looks like they aren't afraid to show the pie.",
                f"{user.mention} and {ctx.author.mention} are fucking like rabbits, looks like they broke the bed. A new bed will be needed.",
                f"{user.mention} bends over {ctx.author.mention} and fucks them raw. ",
                f"{user.mention} pushes {ctx.author.mention} against the wall, choking them and fucking them silly.",
                f"{user.mention} fucks {ctx.author.mention} in the ass, but they accidentally shit the bed.",
                f"{user.mention} fucks {ctx.author.mention} vigorously with a dildo! Jackhammer!",
                f"{user.mention} plows {ctx.author.mention} into the couch before spraying {ctx.author.mention} with their semen!",
                "JESUS CONSENTS, GOD WILLS IT.",
            ]
        else:
            responses = [
                f"Looks like they dont wanna smash, {ctx.author.mention}!",
                f"Guess it's back to the porn mags for you, {ctx.author.mention}. :/",
                "Sucks to be you, buckaroo!",
                "Guess your dick game isn't strong enough.",
                "¯\\\\\\_(ツ)\\_/¯",
                "Haters are your motivators~",
                "Bing bong, they don't want your ding dong!",
                "No means no. Sorry!",
                "I'd love to, but I'm going to have a migraine that night.",
                f"I think I hear someone calling me... way, way over there. *poofs* Sorry {ctx.author.mention}.",
                "Like right now? I don't think that's a great idea, what with my infectious mouth disease and all...",
                "This feels like the beginning of a really great friendship! Ouch.. Friendzoned.",
                "It's not you; it's your facial hair. And your shirt. And your personality.",
                "I'd fuck you, but I'd be afraid of my future children inheriting your face",
                "Oh, wait, I think I just spotted someone else that I'd rather be talking to! That has to sting...",
            ]
        await ctx.send(random.choice(responses))


def setup(bot:utils.Bot):
    x = Simulation(bot)
    bot.add_cog(x)
