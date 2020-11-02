from datetime import datetime as dt

import discord
import voxelbotutils as utils

from cogs import utils as localutils


class ParentCommands(utils.Cog):

    @utils.command()
    @utils.checks.bot_is_ready()
    async def adopt(self, ctx:utils.Context, user:discord.Member):
        """Adopt a user"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # See if they already have a parent
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

        # Get their permissions
        permissions = await localutils.get_perks_for_user(self.bot, user)

        # See how many children they're allowed to have
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=ctx.author.id
        )
        matches = data['results'][0]['data']
        if len(matches) > permissions.max_children:
            return await ctx.send(f"You can only have {permissions.max_children} error.")

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

        # See they already have a parent
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=ctx.author.id
        )
        matches = data['results'][0]['data']
        if matches:
            return await ctx.send("You have a parent error.")

        # See if they're already related
        if await localutils.family.utils.is_related(self.bot, ctx.author, user):
            return await ctx.send("You're already related error.")

        # Get their permissions
        permissions = await localutils.get_perks_for_user(self.bot, user)

        # See how many children they're allowed to have
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user.id
        )
        matches = data['results'][0]['data']
        if len(matches) > permissions.max_children:
            return await ctx.send(f"They can only have {permissions.max_children} error.")

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
    x = ParentCommands(bot)
    bot.add_cog(x)
