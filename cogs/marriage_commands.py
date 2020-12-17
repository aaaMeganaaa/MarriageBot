from datetime import datetime as dt

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class FamilyCommands(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog.
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1, pending_proposal: false})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command(aliases=['propose'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True, external_emojis=True)
    async def marry(self, ctx:utils.Context, user:discord.Member):
        """
        Marries to you another user.
        """

        # Check exemptions
        if user.id == ctx.guild.me.id:
            return await ctx.send("Oh wow. Um. No. No thank you. I'm not interested.")
        elif user.bot:
            return await ctx.send("Bots don't really have a concept of marriage, unfortunately.")
        elif user == ctx.author:
            return await ctx.send("That's highly unlikely to happen.")
        guild_id = localutils.utils.get_guild_id(ctx)

        # Make sure they can't propose to other people
        async with localutils.family.utils.FamilyMemberLock(self.bot, ctx.author, user, guild_id=guild_id):

            # See if they're already married to a maximum amount of people, or to each other
            data = await self.bot.neo4j.cypher(
                r"MATCH (:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:MARRIED_TO]->(n:FamilyTreeMember) RETURN n",
                user_id=ctx.author.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            for m in matches:
                if m['row'][0]['user_id'] == user.id:
                    return await ctx.send("You two are already married .-.")
            permissions = await localutils.get_perks_for_user(self.bot, ctx.author)
            if len(matches) >= permissions.max_partners:
                return await ctx.send(f"Unfortunately, can only marry **{permissions.max_partners}** people.")

            # See if their partner is already married to a maximum amount of people
            data = await self.bot.neo4j.cypher(
                r"MATCH (:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:MARRIED_TO]->(n:FamilyTreeMember) RETURN n",
                user_id=user.id, guild_id=guild_id,
            )
            matches = data['results'][0]['data']
            permissions = await localutils.get_perks_for_user(self.bot, user)
            if len(matches) >= permissions.max_partners:
                return await ctx.send(
                    f"Unfortunately, {user.mention} can only marry **{permissions.max_partners}** people.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

            # See if 're already related
            if await localutils.family.utils.is_related(self.bot, ctx.author, user):
                return await ctx.send("You're already related error.")

            # See if they want to marry
            result = await localutils.utils.send_proposal_message(
                ctx, user, f"Hey, {user.mention}; do you want to marry {ctx.author.mention}?",
            )
            if result is None:
                return

            # Add them to the db
            await self.bot.neo4j.cypher(
                r"""MERGE (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})
                MERGE (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
                MERGE (n)-[:MARRIED_TO {timestamp: $timestamp}]->(m)-[:MARRIED_TO {timestamp: $timestamp}]->(n)""",
                author_id=ctx.author.id, user_id=user.id, guild_id=guild_id, timestamp=dt.utcnow().timestamp(),
            )

        # And we done
        return await ctx.send(f"Heck yeah! {ctx.author.mention}, {user.mention}, I now pronounce you married! :3")

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True, add_reactions=True)
    async def divorce(self, ctx:utils.Context, *, user:discord.User):
        """
        Divorces you form your partner.
        """

        # Grab the guild id
        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user.id

        # See if they're already married
        data = await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})-[:MARRIED_TO]->
            (m:FamilyTreeMember {user_id: $partner_id, guild_id: $guild_id}) RETURN m""",
            author_id=ctx.author.id, partner_id=user_id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"It doesn't actually look like you're married to <@{user_id}>.", allowed_mentions=discord.AllowedMentions.none())

        # Remove them from the db
        await self.bot.neo4j.cypher(
            r"""MATCH (:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id})<-[r:MARRIED_TO]->
            (:FamilyTreeMember {user_id: $partner_id, guild_id: $guild_id}) DELETE r""",
            author_id=ctx.author.id, partner_id=user_id, guild_id=guild_id,
        )

        # And done
        return await ctx.send(
            f"Sad times. I've divorced you from <@{user_id}>, {ctx.author.mention} :<",
            allowed_mentions=localutils.utils.only_mention(ctx.author),
        )


def setup(bot:utils.Bot):
    x = FamilyCommands(bot)
    bot.neo4j = aioneo4j.Neo4j(**bot.config['neo4j'])
    bot.add_cog(x)
