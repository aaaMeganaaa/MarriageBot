import asyncio
import io
import json

import aioneo4j
import discord
from discord.ext import commands
import voxelbotutils as utils

from cogs import utils as localutils


class Information(utils.Cog):

    async def cache_setup(self, db):
        """
        Set up the cache stuff needed for this cog.
        """

        # We need to run this or gds complains that none of the paths exist
        await self.bot.neo4j.cypher(
            r"""MERGE (u:FamilyTreeMember {user_id: -1, guild_id: -1})
            MERGE (u)-[:MARRIED_TO]->(u)-[:PARENT_OF]->(u)-[:CHILD_OF]->(u)"""
        )

    @utils.command(aliases=['partners', 'wife', 'wives', 'husband', 'husbands', 'spouse', 'spouses'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def partner(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Tells you who a given user's partner is.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user_id or ctx.author.id
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:MARRIED_TO]->(m:FamilyTreeMember) RETURN m",
            user_id=user_id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            if user_id == ctx.author.id:
                return await ctx.send("You aren't married to anyone :<")
            return await ctx.send(f"<@{user_id}> isn't married to anyone :<", allowed_mentions=discord.AllowedMentions.none())
        partner_ids = sorted([i['row'][0]['user_id'] for i in matches])
        partner_mentions = [f"<@{i}>" for i in partner_ids]
        if user_id == ctx.author.id:
            return await ctx.send(f"You're married to {localutils.human_join(partner_mentions)}.", allowed_mentions=discord.AllowedMentions.none())
        return await ctx.send(f"<@{user_id}> is married to {localutils.human_join(partner_mentions)}.", allowed_mentions=discord.AllowedMentions.none())

    @utils.command(aliases=['kids', 'child'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def children(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Gives you a list of someone's children.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user_id or ctx.author.id
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:PARENT_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user_id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            if user_id == ctx.author.id:
                return await ctx.send("You don't have any children :<")
            return await ctx.send(f"<@{user_id}> has no children :<", allowed_mentions=discord.AllowedMentions.none())
        uids = []
        for row in matches:
            uids.append(f"<@{row['row'][0]['user_id']}>")
        if user_id == ctx.author.id:
            return await ctx.send(f"You're the parent of {localutils.human_join(uids)}.", allowed_mentions=discord.AllowedMentions.none())
        return await ctx.send(f"<@{user_id}> is parent of {localutils.human_join(uids)}.", allowed_mentions=discord.AllowedMentions.none())

    @utils.command(aliases=['relation'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def relationship(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Tells you if you're related to a user.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        text = await localutils.family.utils.get_relationship(self.bot, ctx.author, discord.Object(user_id), guild_id=guild_id)
        return await ctx.send(" ".join(text) if text else "You aren't related.")

    @utils.command(aliases=['fs', 'treesize', 'ts'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def familysize(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Tells you if you're related to a user.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user_id or ctx.author.id
        blood_size = await localutils.family.utils.get_blood_family_size(self.bot, discord.Object(user_id), guild_id=guild_id)
        full_size = await localutils.family.utils.get_family_size(self.bot, discord.Object(user_id), guild_id=guild_id)
        if user_id == ctx.author.id:
            return await ctx.send(f"Your family size is **{blood_size} blood relatives** and **{full_size} general relatives**.")
        return await ctx.send(
            f"<@{user_id}>'s family size is **{blood_size} blood relatives** and **{full_size} general relatives**.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @utils.command(aliases=['mother', 'father', 'mom', 'dad', 'mum'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def parent(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Tells you who a given user's parent is.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user_id or ctx.author.id
        data = await self.bot.neo4j.cypher(
            r"MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:CHILD_OF]->(m:FamilyTreeMember) RETURN m",
            user_id=user_id, guild_id=guild_id,
        )
        matches = data['results'][0]['data']
        if not matches:
            if user_id == ctx.author.id:
                return await ctx.send("You don't have a parent :<")
            return await ctx.send(f"<@{user_id}> has no parent :<", allowed_mentions=discord.AllowedMentions.none())
        if user_id == ctx.author.id:
            return await ctx.send(f"You're the child of <@{matches[0]['row'][0]['user_id']}>.", allowed_mentions=discord.AllowedMentions.none())
        return await ctx.send(f"<@{user_id}> is the child of <@{matches[0]['row'][0]['user_id']}>.", allowed_mentions=discord.AllowedMentions.none())

    @utils.command(aliases=['t', 'familytree'])
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def tree(self, ctx:utils.Context, *, user_id:utils.converters.UserID=None):
        """
        Tells you if you're related to a user.
        """

        engine = 'dot'  # engine.lower()
        if engine not in ['dot', 'neato', 'fdp', 'sfdp', 'twopi', 'circo', 'patchwork', 'osage']:
            return await ctx.send("The Graphviz engine you provided isn't valid.")

        # Write to file
        guild_id = localutils.utils.get_guild_id(ctx)
        user_id = user_id or ctx.author.id
        v = await self.get_tree_dot(ctx, user_id, guild_id=guild_id)
        if v is None:
            if user_id == ctx.author.id:
                return await ctx.send("You have no family which I can graph.")
            return await ctx.send(f"<@{user_id}> has no family which I can graph.", allowed_mentions=discord.AllowedMentions.none())
        else:
            dot, user_count, root_user_id = v
        try:
            with open(f'{ctx.author.id}.gz', 'w', encoding='utf-8') as a:
                a.write(dot)
        except Exception as e:
            self.logger.error(f"Could not write to {ctx.author.id}.gz")
            raise e

        # Convert to an image
        dot_process = await asyncio.create_subprocess_exec(*[
            engine, '-Tpng', f'{ctx.author.id}.gz', '-o', f'{ctx.author.id}.png', '-Gcharset=UTF-8',
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
            f"Showing **{await localutils.family.utils.get_blood_family_size(self.bot, root_user)}** of "
            f"**{await localutils.family.utils.get_family_size(self.bot, root_user)}** family members."
        )

        # Output file
        file = discord.File(f"{ctx.author.id}.png", filename="tree.png")
        await ctx.send(flavour_text, file=file)

        # Delete what we worked with
        self.bot.loop.create_task(asyncio.create_subprocess_exec(*['rm', f'{ctx.author.id}.png']))
        self.bot.loop.create_task(asyncio.create_subprocess_exec(*['rm', f'{ctx.author.id}.gz']))

    @utils.command(hidden=True)
    @commands.bot_has_permissions(attach_files=True)
    @commands.is_owner()
    @utils.checks.bot_is_ready()
    @commands.bot_has_permissions(send_messages=True)
    async def rawtree(self, ctx:utils.Context, user_id:utils.converters.UserID=None):
        """
        Tells you if you're related to a user.
        """

        guild_id = localutils.utils.get_guild_id(ctx)
        v = await self.get_tree_dot(ctx, user_id, guild_id=guild_id)
        if v is None:
            return await ctx.send("You have no family which I can graph.")
        else:
            dot, user_count, root_user_id = v
        file = discord.File(io.StringIO(dot), filename="dot.gz")
        return await ctx.send(file=file)

    async def get_tree_dot(self, ctx, user_id:int, guild_id:int=0):
        """
        Gets a fully written dot script for a given user's tree.
        """

        # Get dot script
        user_id = user_id or ctx.author.id
        root_user_id = await localutils.family.utils.get_tree_root_user_id(self.bot, discord.Object(user_id), guild_id=guild_id)
        root_user = discord.Object(root_user_id)
        family = await localutils.family.utils.get_tree_expanded_from_root(self.bot, root_user, guild_id=guild_id)
        root_family_member_object = localutils.family.FamilyMember.get_family_from_cypher(family, root_user_id=root_user_id)
        if root_family_member_object is None:
            return None
        async with self.bot.database() as db:
            tree_display = await localutils.family.CustomTreeDisplay.fetch_custom_tree(db, ctx.author.id)
        tree_display.highlighted_user_id = user_id
        dot, user_count = await localutils.family.FamilyMemberDotGenerator.expand_downwards_to_dot(root_family_member_object, tree_display=tree_display)
        return dot, user_count, root_user_id

    @utils.command()
    @utils.checks.bot_is_ready()
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def cypher(self, ctx:utils.Context, *, cypher:str):
        """Leave your parent"""

        # See if they're already married
        async with ctx.typing():
            try:
                data = await self.bot.neo4j.cypher(cypher)
            except aioneo4j.errors.ClientError as e:
                return await ctx.send(str(e))
            await ctx.send(f"`data['results'][0]['data']` == ```json\n{json.dumps(data['results'][0]['data'], indent=4)}```")

    @utils.Cog.listener()
    async def on_message(self, message):
        """Store usernames in their family tree nodes"""

        await self.bot.neo4j.cypher(
            r"""MATCH (n:FamilyTreeMember {user_id: $user_id}) SET n.username=$username""",
            user_id=message.author.id, username=str(message.author)
        )


def setup(bot:utils.Bot):
    x = Information(bot)
    bot.add_cog(x)
