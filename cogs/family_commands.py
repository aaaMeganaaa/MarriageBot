from datetime import datetime as dt

import aioneo4j
import discord
import voxelbotutils as utils

from cogs import utils as localutils


class FamilyCommands(utils.Cog):

    MAXIMUM_MARRIAGE_COUNT = 2

    async def cache_setup(self, db):
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

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {guild_id: 0})-[:MARRIED_TO]->(:FamilyTreeMember) WHERE n.user_id in [$author_id, $user_id] RETURN n",
            author_id=ctx.author.id, user_id=user.id
        )
        matches = data['results'][0]['data']
        if len(matches) >= self.MAXIMUM_MARRIAGE_COUNT:
            return await ctx.send(f"You can only marry {self.MAXIMUM_MARRIAGE_COUNT} people error")

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

    @utils.command(aliases=['mother', 'father', 'mom', 'dad', 'mum'])
    @utils.checks.bot_is_ready()
    async def parent(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """Tells you who a given user's parent is"""

        user_id = user_id or ctx.author.id
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"<@{user_id}> has no parent error.", allowed_mentions=discord.AllowedMentions(users=False))
        return await ctx.send(f"<@{user_id}> is the child of to <@{matches[0]['row'][0]['user_id']}>.", allowed_mentions=discord.AllowedMentions(users=False))

    @utils.command()
    @utils.checks.bot_is_ready()
    async def adopt(self, ctx:utils.Context, user:discord.Member):
        """Adopt a user"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user.id
        )
        matches = data['results'][0]['data']
        if matches:
            return await ctx.send("They have a parent error.")

        # See if they're already related
        if await localutils.family.utils.is_related(self.bot, ctx.author, user):
            return await ctx.send("You're already related error.")

        # Add them to the db
        data = await self.bot.neo4j.cypher(
            r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0}) MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0})
            MERGE (n)-[:PARENT_OF {timestamp: $timestamp}]->(m)-[:CHILD_OF {timestamp: $timestamp}]->(n)""",
            author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
        )
        return await ctx.send("Added to database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    async def makeparent(self, ctx:utils.Context, user:discord.Member):
        """Make a user your parent"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user.id
        )
        matches = data['results'][0]['data']
        if matches:
            return await ctx.send("You have a parent error.")

        # See if they're already related
        if await localutils.family.utils.is_related(self.bot, ctx.author, user):
            return await ctx.send("You're already related error.")

        # Add them to the db
        await self.bot.neo4j.cypher(
            r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0}) MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0})
            MERGE (n)-[:CHILD_OF {timestamp: $timestamp}]->(m)-[:PARENT_OF {timestamp: $timestamp}]->(n)""",
            author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
        )
        return await ctx.send("Added to database.")

    @utils.command(aliases=['runaway', 'leaveparent'])
    @utils.checks.bot_is_ready()
    async def emancipate(self, ctx:utils.Context):
        """Leave your parent"""

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            author_id=ctx.author.id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send("You're not adopted error.")
        parent_id = matches[0]['row'][0]['user_id']

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[r:CHILD_OF]->(:FamilyTreeMember)-[t:PARENT_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, parent_id=parent_id
        )
        return await ctx.send("Deleted from database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    async def disown(self, ctx:utils.Context, user_id:utils.converters.UserID):
        """Leave your parent"""

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember {user_id: $user_id}) RETURN m",
            author_id=ctx.author.id, user_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send("You're not their parent error.")
        child_id = matches[0]['row'][0]['user_id']

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[r:PARENT_OF]->(:FamilyTreeMember)-[t:CHILD_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, parent_id=child_id
        )
        return await ctx.send("Deleted from database.")


def setup(bot:utils.Bot):
    x = FamilyCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
