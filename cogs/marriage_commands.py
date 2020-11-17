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
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command(aliases=['propose'])
    @utils.checks.bot_is_ready()
    async def marry(self, ctx:utils.Context, user:discord.Member):
        """Marries to you another user"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

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

        # Add them to the db
        await self.bot.neo4j.cypher(
            r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0}) MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0})
            MERGE (n)-[:MARRIED_TO {timestamp: $timestamp}]->(m)-[:MARRIED_TO {timestamp: $timestamp}]->(n)""",
            author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
        )
        return await ctx.send("Added to database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    async def divorce(self, ctx:utils.Context, user_id:commands.Greedy[utils.converters.UserID]):
        """Divorces you form your partner"""

        # Make sure they said someone
        if not user_id:
            raise utils.errors.MissingRequiredArgumentString("user_id")

        # See if they're already married
        for single_user_id in user_id:
            data = await self.bot.neo4j.cypher(
                r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:MARRIED_TO]->(m:FamilyTreeMember {user_id: $partner_id, guild_id: 0})
                RETURN m""",
                author_id=ctx.author.id, partner_id=single_user_id
            )
            matches = data['results'][0]['data']
            if not matches:
                return await ctx.send(f"You're not married to {single_user_id} error.")

        # Remove them from the db
        for single_user_id in user_id:
            await self.bot.neo4j.cypher(
                r"""MATCH (:FamilyTreeMember {user_id: $author_id, guild_id: 0})<-[r:MARRIED_TO]->(:FamilyTreeMember {user_id: $partner_id, guild_id: 0}) DELETE r""",
                author_id=ctx.author.id, partner_id=single_user_id
            )

        # And done
        return await ctx.send(f"Deleted {len(user_id)} field(s) from database.")


def setup(bot:utils.Bot):
    x = FamilyCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
