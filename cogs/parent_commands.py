import asyncio
from datetime import datetime as dt

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class ParentCommands(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1, pending_proposal: false})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def adopt(self, ctx:utils.Context, user:discord.Member):
        """Adopt a user"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=0):

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
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)

            # See how many children they're allowed to have
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=ctx.author.id
            )
            matches = data['results'][0]['data']
            if len(matches) > permissions.max_children:
                return await ctx.send(f"You can only have {permissions.max_children} error.")

            # See if they want to adopt
            message = await ctx.send(f"{user.mention} do you want to be the child of {ctx.author.mention} message")
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
            data = await self.bot.neo4j.cypher(
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0, pending_proposal: false})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0, pending_proposal: false})
                MERGE (n)-[:PARENT_OF {timestamp: $timestamp}]->(m)-[:CHILD_OF {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
            )

        # And we're done
        return await ctx.send("Added to database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def makeparent(self, ctx:utils.Context, user:discord.Member):
        """Make a user your parent"""

        # Check exemptions
        if user.bot or user == ctx.author:
            return await ctx.send("Invalid user error.")

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=0):

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
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)

            # See how many children they're allowed to have
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=user.id
            )
            matches = data['results'][0]['data']
            if len(matches) > permissions.max_children:
                return await ctx.send(f"They can only have {permissions.max_children} error.")

            # See if they want to adopt
            message = await ctx.send(f"{user.mention} do you want to be the parent of {ctx.author.mention} message")
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
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: 0, pending_proposal: false})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: 0, pending_proposal: false})
                MERGE (n)-[:CHILD_OF {timestamp: $timestamp}]->(m)-[:PARENT_OF {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, timestamp=dt.utcnow().timestamp()
            )

        # And we're done
        return await ctx.send("Added to database.")

    @utils.command(aliases=['runaway', 'leaveparent'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
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
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[r:CHILD_OF]->
            (:FamilyTreeMember)-[t:PARENT_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, parent_id=parent_id
        )
        return await ctx.send("Deleted from database.")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def disown(self, ctx:utils.Context, *, user_id:utils.converters.UserID):
        """Leave your parent"""

        # Make sure they said someone
        if not user_id:
            raise utils.errors.MissingRequiredArgumentString("user_id")

        # Check they're actually a parent
        data = await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[:PARENT_OF]->
            (m:FamilyTreeMember {user_id: $user_id, guild_id: 0}) RETURN m""",
            author_id=ctx.author.id, user_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"You're not the parent of {user_id} error.")

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: 0})-[r:PARENT_OF]->
            (:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[t:CHILD_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, user_id=user_id
        )

        # And done
        return await ctx.send("Deleted field from database.")


def setup(bot:utils.Bot):
    x = ParentCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
