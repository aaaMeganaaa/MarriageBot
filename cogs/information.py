import asyncio
import io

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class Information(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command(aliases=['partners', 'wife', 'wives', 'husband', 'husbands', 'spouse', 'spouses'])
    @utils.checks.bot_is_ready()
    async def partner(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """Tells you who a given user's partner is"""

        user_id = user_id or ctx.author.id
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:MARRIED_TO]->(m:FamilyTreeMember) RETURN m",
            user_id=user_id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"<@{user_id}> isn't married error.", allowed_mentions=discord.AllowedMentions.none())
        partner_ids = sorted([i['row'][0]['user_id'] for i in matches])
        partner_mentions = [f"<@{i}>" for i in partner_ids]
        return await ctx.send(f"<@{user_id}> is married to {localutils.human_join(partner_mentions)}.", allowed_mentions=discord.AllowedMentions.none())

    @utils.command(aliases=['kids', 'child'])
    @utils.checks.bot_is_ready()
    async def children(self, ctx:utils.Context, user:discord.Member=None):
        """Gives you a list of someone's children"""

        user = user or ctx.author
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: 0})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user.id
        )
        matches = data['results'][0]['data']
        if not matches:
            return await ctx.send(f"{user.mention} has no children error.", allowed_mentions=discord.AllowedMentions.none())
        uids = []
        for row in matches:
            uids.append(f"<@{row['row'][0]['user_id']}>")
        return await ctx.send(f"{user.mention} is parent of {localutils.human_join(uids)}.", allowed_mentions=discord.AllowedMentions.none())

    @utils.command(aliases=['relation'])
    @utils.checks.bot_is_ready()
    async def relationship(self, ctx:utils.Context, user:discord.Member):
        """Tells you if you're related to a user"""

        return await ctx.send(await localutils.family.utils.get_relationship(self.bot, ctx.author, user) or "You aren't related.")

    @utils.command(aliases=['fs', 'treesize', 'ts'])
    @utils.checks.bot_is_ready()
    async def familysize(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """Tells you if you're related to a user"""

        user_id = user_id or ctx.author.id
        blood_size = await localutils.family.utils.get_blood_family_size(self.bot, discord.Object(user_id))
        full_size = await localutils.family.utils.get_family_size(self.bot, discord.Object(user_id))
        return await ctx.send(f"<@{user_id}>'s family size is {blood_size} blood relatives and {full_size} general relatives.", allowed_mentions=discord.AllowedMentions.none())

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

    @utils.command(aliases=['t', 'familytree'])
    @utils.checks.bot_is_ready()
    async def tree(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """Tells you if you're related to a user"""

        # Write to file
        v = await self.get_tree_dot(ctx, user_id)
        if v is None:
            return await ctx.send("You have no family which I can graph.")
        else:
            dot, user_count, root_user_id = v
        try:
            with open(f'{ctx.author.id}.gz', 'w', encoding='utf-8') as a:
                a.write(dot)
        except Exception as e:
            self.logger.error(f"Could not write to {self.bot.config['tree_file_location']}/{ctx.author.id}.gz")
            raise e

        # Convert to an image
        dot_process = await asyncio.create_subprocess_exec(*[
            'dot', '-Tpng', f'{ctx.author.id}.gz', '-o', f'{ctx.author.id}.png', '-Gcharset=UTF-8',
        ])
        try:
            await asyncio.wait_for(dot_process.wait(), 15)
        except asyncio.TimeoutError:
            pass
        try:
            dot_process.kill()
        except ProcessLookupError:
            pass  # It already died
        except Exception as e:
            raise e

        # Generate flavourtext
        root_user = discord.Object(root_user_id)
        flavour_text = (
            f"Showing {await localutils.family.utils.get_blood_family_size(self.bot, root_user)} of "
            f"{await localutils.family.utils.get_family_size(self.bot, root_user)} family members."
        )

        # Output file
        file = discord.File(f"{ctx.author.id}.png", filename="tree.png")
        return await ctx.send(flavour_text, file=file)

    @utils.command(hidden=True)
    @commands.bot_has_permissions(attach_files=True)
    @commands.is_owner()
    @utils.checks.bot_is_ready()
    async def rawtree(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """Tells you if you're related to a user"""

        v = await self.get_tree_dot(ctx, user_id)
        if v is None:
            return await ctx.send("You have no family which I can graph.")
        else:
            dot, user_count, root_user_id = v
        file = discord.File(io.StringIO(dot), filename="dot.gz")
        return await ctx.send(file=file)

    async def get_tree_dot(self, ctx, user_id):
        """
        Gets a fully written dot script for a given user's tree.
        """

        # Get dot script
        user_id = user_id or ctx.author.id
        root_user_id = await localutils.family.utils.get_tree_root_user_id(self.bot, discord.Object(user_id))
        root_user = discord.Object(root_user_id)
        family = await localutils.family.utils.get_tree_expanded_from_root(self.bot, root_user)
        root_family_member_object = localutils.family.FamilyMember.get_family_from_cypher(family, root_user_id=root_user_id)
        if root_family_member_object is None:
            return None
        dot, user_count = await localutils.family.FamilyMemberDotGenerator.expand_downwards_to_dot(root_family_member_object)
        return dot, user_count, root_user_id

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.is_owner()
    async def cypher(self, ctx:utils.Context, *, cypher:str):
        """Leave your parent"""

        # See if they're already married
        await ctx.send("running")
        try:
            data = await self.bot.neo4j.cypher(cypher)
        except aioneo4j.errors.ClientError as e:
            return await ctx.send(str(e))
        return await ctx.send(data['results'][0]['data'])

    @utils.Cog.listener()
    @utils.checks.bot_is_ready()
    async def on_message(self, message):
        """Store usernames in their family tree nodes"""

        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $user_id}) SET n.username=$username""",
            user_id=message.author.id, username=str(message.author)
        )


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
