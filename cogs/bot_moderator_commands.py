from datetime import datetime as dt

from discord.ext import commands
import voxelbotutils as utils

import utils as localutils


class BotModeratorCommands(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog.
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1, pending_proposal: false})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command()
    @commands.has_role("MarriageBot Moderator")
    @commands.bot_has_permissions(send_messages=True)
    @utils.checks.is_config_set("is_server_specific")
    async def forcemarry(self, ctx:utils.Context, user_a:utils.converters.UserID, user_b:utils.converters.UserID=None):
        """Marries the two specified users"""

        # Correct params
        if user_b is None:
            user_a, user_b = ctx.author.id, user_a

        # Fix things that so obviously cause errors
        if user_a == user_b:
            return await ctx.send("You can't marry yourself.")

        # Add them to the db
        await self.bot.neo4j.cypher(
            r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})
            MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
            MERGE (n)-[:MARRIED_TO {timestamp: $timestamp}]->(m)-[:MARRIED_TO {timestamp: $timestamp}]->(n)""",
            author_id=user_a, user_id=user_b, guild_id=localutils.utils.get_guild_id(ctx), timestamp=dt.utcnow().timestamp(),
        )

    @utils.command()
    @commands.has_role("MarriageBot Moderator")
    @commands.bot_has_permissions(send_messages=True)
    @utils.checks.is_config_set("is_server_specific")
    async def forcedivorce(self, ctx:utils.Context, user:utils.converters.UserID):
        """Divorces a user from their spouse"""

        pass

    @utils.command()
    @commands.has_role("MarriageBot Moderator")
    @commands.bot_has_permissions(send_messages=True)
    @utils.checks.is_config_set("is_server_specific")
    async def forceadopt(self, ctx:utils.Context, parent:utils.converters.UserID, child:utils.converters.UserID=None):
        """Adds the child to the specified parent"""

        # Correct params
        if child is None:
            parent, child = ctx.author.id, parent

        pass

    @utils.command(aliases=["forceeman"])
    @commands.has_role("MarriageBot Moderator")
    @commands.bot_has_permissions(send_messages=True)
    @utils.checks.is_config_set("is_server_specific")
    async def forceemancipate(self, ctx:utils.Context, user:utils.converters.UserID):
        """
        Force emancipates a child.
        """

        pass


def setup(bot:utils.Bot):
    x = BotModeratorCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
