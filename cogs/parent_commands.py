from datetime import datetime as dt

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class ParentCommands(utils.Cog):

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
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def adopt(self, ctx:utils.Context, user:discord.Member):
        """
        Adopt a user.
        """

        # Check exemptions
        if user.id == ctx.guild.me.id:
            return await ctx.send("Ha. No. I can do better than you, I feel. Thanks.")
        elif user.bot:
            return await ctx.send("You can't adopt bots, I'm afraid :<")
        elif user == ctx.author:
            return await ctx.send("Unlikely.")
        guild_id = localutils.utils.get_guild_id(ctx)

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=guild_id):

            # See if they already have a parent
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=user.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            if matches[0]['row'][0]['user_id'] == user.id:
                return await ctx.send("They're already your child .-.")
            if matches:
                return await ctx.send(
                    f"Sorry, {ctx.author.mention}, it looks like {user.mention} already has a parent :<",
                    allowed_mentions=localutils.utils.only_mention(ctx.author)
                )

            # See if they're already related
            if await localutils.family.utils.is_related(self.bot, ctx.author, user):
                return await ctx.send(
                    f"It looks like you're already related! Run ``{ctx.clean_prefix}relationship @{ctx.author!s} @{user!s}`` to see how, if you don't know."
                )

            # Get their permissions
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)

            # See how many children they're allowed to have
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=ctx.author.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            if len(matches) > permissions.max_children:
                return await ctx.send(f"Sorry, {ctx.author.mention}; you can only have **{permissions.max_children}** children :<")

            # See if they want to adopt
            result = await localutils.utils.send_proposal_message(
                ctx, user, f"Hey, {user.mention}, do you want to let {ctx.author.mention} adopt you?",
            )
            if result is None:
                return

            # Add them to the db
            data = await self.bot.neo4j.cypher(
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
                MERGE (n)-[:PARENT_OF {timestamp: $timestamp}]->(m)-[:CHILD_OF {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, guild_id=guild_id, timestamp=dt.utcnow().timestamp(),
            )

        # And we're done
        return await ctx.send(f"Heck yeah! {ctx.author.mention}, say hello to your new child, {user.mention}!")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def makeparent(self, ctx:utils.Context, user:discord.Member):
        """
        Make a user your parent.
        """

        # Check exemptions
        if user.id == ctx.guild.me.id:
            return await ctx.send("Hmmmmmm I'm flattered, but no. I'm okay. Thank you.")
        elif user == ctx.author:
            return await ctx.send("Unlikely.")
        guild_id = localutils.utils.get_guild_id(ctx)

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=guild_id):

            # See they already have a parent
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=ctx.author.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            if matches[0]['row'][0]['user_id'] == user.id:
                return await ctx.send("They're already your parent .-.")
            if matches:
                return await ctx.send("It looks like you already have a parent, unfortunately!")

            # See if they're already related
            if await localutils.family.utils.is_related(self.bot, ctx.author, user):
                return await ctx.send(
                    f"It looks like you're already related! Run ``{ctx.clean_prefix}relationship @{ctx.author!s} @{user!s}`` to see how, if you don't know."
                )

            # Get their permissions
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)

            # See how many children they're allowed to have
            data = await self.bot.neo4j.cypher(
                r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
                user_id=user.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            if len(matches) > permissions.max_children:
                return await ctx.send(
                    f"Sorry, {ctx.author.mention}; they already have **{permissions.max_children}** children - they're at their maximum :<"
                )

            # See if they want to adopt
            result = await localutils.utils.send_proposal_message(
                ctx, user, f"Hey, {user.mention}, do you want to adopt {ctx.author.mention}?",
            )
            if result is None:
                return

            # Add them to the db
            await self.bot.neo4j.cypher(
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
                MERGE (n)-[:CHILD_OF {timestamp: $timestamp}]->(m)-[:PARENT_OF {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, guild_id=guild_id, timestamp=dt.utcnow().timestamp(),
            )

        # And we're done
        return await ctx.send(f"Heck yeah! {ctx.author.mention}, say hello to your new parent, {user.mention}!")

    @utils.command(aliases=['runaway', 'leaveparent'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def emancipate(self, ctx:utils.Context):
        """
        Leave your parent.
        """

        # Grab the guild id
        guild_id = localutils.utils.get_guild_id(ctx)

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            author_id=ctx.author.id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send("It doesn't look like you have a parent, actually :/")
        parent_id = matches[0]['row'][0]['user_id']

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})-[r:CHILD_OF]->
            (:FamilyTreeMember)-[t:PARENT_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, parent_id=parent_id, guild_id=guild_id,
        )
        return await ctx.send(f"Alright, {ctx.author.mention}; I've removed your parent :<")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def disown(self, ctx:utils.Context, *, user_id:utils.converters.UserID):
        """
        Leave your parent.
        """

        # Make sure they said someone
        guild_id = localutils.utils.get_guild_id(ctx)

        # Check they're actually a parent
        data = await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})-[:PARENT_OF]->
            (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id}) RETURN m""",
            author_id=ctx.author.id, user_id=user_id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(
                f"If doesn't look like you're the parent of <@{user_id}>, actually :/",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})-[r:PARENT_OF]->
            (:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[t:CHILD_OF]->(n) DELETE r, t""",
            author_id=ctx.author.id, user_id=user_id, guild_id=guild_id,
        )

        # And done
        return await ctx.send(
            f"Alright, {ctx.author.mention}; I've disowned <@{user_id}> from you :<",
            allowed_mentions=localutils.utils.only_mention(ctx.author),
        )


def setup(bot:utils.Bot):
    x = ParentCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
