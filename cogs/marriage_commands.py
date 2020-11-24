import asyncio
from datetime import datetime as dt

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class FamilyCommands(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1, pending_proposal: false})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command(aliases=['propose'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def marry(self, ctx:utils.Context, user:discord.Member):
        """Marries to you another user"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=0):

            # Get their permissions
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)

            # See if they're already married
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {guild_id: 0})-[:MARRIED_TO]->(:FamilyTreeMember) WHERE n.user_id in [$author_id, $user_id] RETURN n",
                author_id=ctx.author.id, user_id=user.id
            )
            matches = data['results'][0]['data']
            if len(matches) >= permissions.max_partners:
                return await ctx.send(f"You can only marry {permissions.max_partners} people error")

            # See if they're already related
            if await localutils.family.utils.is_related(self.bot, ctx.author, user):
                return await ctx.send("You're already related error.")

            # See if they want to marry
            message = await ctx.send(f"{user.mention} do you want to marry {ctx.author.mention} message")
            localutils.utils.TickPayloadCheckResult.add_tick_emojis_non_async(message)
            try:
                check = lambda p: p.user_id == user.id and p.message_id == message.id and localutils.utils.TickPayloadCheckResult.from_payload(p)
                payload = await self.bot.wait_for("raw_reaction_add", check=check, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(f"{ctx.author.mention} your proposal timed out error")

            # Check what they said
            result = localutils.utils.TickPayloadCheckResult.from_payload(payload)
            if not result.is_tick:
                return await ctx.send(f"{ctx.author.mention} they said no message")

            # Add them to the db
            await self.bot.neo4j.cypher(
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0})
                MERGE (n)-[:MARRIED_TO {timestamp: $timestamp}]->(m)-[:MARRIED_TO {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
            )

        # And we done
        return await ctx.send("Added to database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def divorce(self, ctx:utils.Context, *, user_id:utils.converters.UserID):
        """Divorces you form your partner"""

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:MARRIED_TO]->
            (m:FamilyTreeMember {user_id: $partner_id, guild_id: 0}) RETURN m""",
            author_id=ctx.author.id, partner_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"You're not married to {user_id} error.")

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (:FamilyTreeMember {user_id: $author_id, guild_id: 0})<-[r:MARRIED_TO]->
            (:FamilyTreeMember {user_id: $partner_id, guild_id: 0}) DELETE r""",
            author_id=ctx.author.id, partner_id=user_id
        )

        # And done
        return await ctx.send("Deleted field from database.")


def setup(bot:utils.Bot):
    x = FamilyCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
