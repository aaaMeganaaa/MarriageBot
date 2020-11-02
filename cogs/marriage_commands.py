from datetime import datetime as dt

import aioneo4j
import discord
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
        permissions = await localutils.get_perks_for_user(self.bot, user)

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
    async def divorce(self, ctx:utils.Context, user_id:utils.converters.UserID):
        """Divorces you form your partner"""

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:MARRIED_TO]->(m:FamilyTreeMember {user_id: $partner_id, guild_id: 0})
            RETURN m""",
            author_id=ctx.author.id, partner_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send("You're not married error.")

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (:FamilyTreeMember {user_id: $author_id, guild_id: 0})<-[r:MARRIED_TO]->(:FamilyTreeMember {user_id: $partner_id}) DELETE r""",
            author_id=ctx.author.id, partner_id=user_id
        )
        return await ctx.send("Deleted from database.")


def setup(bot:utils.Bot):
    x = FamilyCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
