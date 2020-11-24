import typing
import string
import random

import discord
from discord.ext import commands

from .relationship_type import RelationshipType
from .family_relationship import FamilyRelationship


def get_random_string(k=10):
    return ''.join(random.choices(string.ascii_letters, k=10))


async def is_related(bot, user, user2, guild_id:int=0) -> typing.List[dict]:
    """
    A cypher to grab the shortest path from one user to another user.
    If there is no relationship between the two users, an empty list will be returned (falsy).
    """

    data = await bot.neo4j.cypher(
        r"""MATCH (n:FamilyTreeMember {user_id: $author_id, guild_id: $guild_id}), (m:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
        CALL gds.alpha.shortestPath.stream({
            nodeProjection: 'FamilyTreeMember',
            relationshipWeightProperty: null,
            relationshipProjection: {
                MARRIED_TO: {type: 'MARRIED_TO', orientation: 'UNDIRECTED'},
                CHILD_OF: {type: 'CHILD_OF', orientation: 'UNDIRECTED'},
                PARENT_OF: {type: 'PARENT_OF', orientation: 'UNDIRECTED'}
            }, startNode: n, endNode: m
        }) YIELD nodeId
        RETURN gds.util.asNode(nodeId)""",
        author_id=user.id, user_id=user2.id, guild_id=guild_id
    )
    matches = data['results'][0]['data']
    return matches


async def get_tree_root_user_id(bot, user, guild_id:int=0) -> int:
    """
    A cypher to grab the root user of a given member's family tree when spanned up through their parentage line.
    """

    data = await bot.neo4j.cypher(
        r"""MATCH (n:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})-[:CHILD_OF*]->(m:FamilyTreeMember {guild_id: $guild_id}) RETURN m""",
        user_id=user.id, guild_id=guild_id
    )
    matches = data['results'][0]['data']
    if matches:
        return matches[-1]['row'][0]['user_id']
    return user.id


async def get_tree_expanded_from_root(bot, root_user, guild_id:int=0) -> typing.List:
    """
    A cypher that will take a root user and expand _downwards_ from them to give a tree of blood
    relations as a list of FamilyRelationships.
    """

    output_data = []
    processed_users = []
    uids = [root_user.id]
    while uids:
        data = await bot.neo4j.cypher(
            r"""UNWIND $user_ids AS X MATCH (n:FamilyTreeMember {user_id: X, guild_id: $guild_id})-[r:PARENT_OF|MARRIED_TO]->(m:FamilyTreeMember {guild_id: $guild_id}) RETURN n, type(r), m""",
            user_ids=uids, guild_id=guild_id
        )
        processed_users.extend(uids)
        uids.clear()
        for return_value in data['results'][0]['data']:
            n, r, m = return_value['row']
            relationship = FamilyRelationship(n['user_id'], n.get('username'), RelationshipType[r], m['user_id'], m.get('username'))
            if relationship not in output_data:
                output_data.append(relationship)
            if n['user_id'] not in processed_users:
                uids.append(n['user_id'])
            if m['user_id'] not in processed_users:
                uids.append(m['user_id'])
    return output_data


async def get_all_family_member_nodes(bot, user, guild_id:int=0) -> typing.List[dict]:
    """
    A cypher that calls the deltaStepping algorithm to grab all the users in a
    given family's tree.
    """

    data = await bot.neo4j.cypher(
        r"""MATCH (u:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
        CALL gds.alpha.shortestPath.deltaStepping.stream({
            startNode: u,
            nodeProjection: 'FamilyTreeMember',
            relationshipProjection: {
                MARRIED_TO: {type: 'MARRIED_TO', orientation: 'NATURAL'},
                CHILD_OF: {type: 'CHILD_OF', orientation: 'NATURAL'},
                PARENT_OF: {type: 'PARENT_OF', orientation: 'NATURAL'}
            },
            delta: 1.0
        }) YIELD nodeId, distance
        WHERE distance < gds.util.infinity()
        RETURN gds.util.asNode(nodeId), distance""",
        user_id=user.id, guild_id=guild_id
    )
    matches = data['results'][0]['data']
    return matches


async def is_family_pending_proposal(bot, user, guild_id:int=0) -> typing.List[dict]:
    """
    A cypher that calls the deltaStepping algorithm to grab all the users in a
    given family's tree.
    """

    all_family_nodes = await get_all_family_member_nodes(bot, user, guild_id)
    for row in all_family_nodes:
        if row["row"][0].get("pending_proposal"):
            return True
    return False


async def get_blood_family_member_nodes(bot, user, guild_id:int=0) -> typing.List[dict]:
    """
    A cypher that'll call the deltaStepping algorithm to be able to grab every node from
    a give user's family tree.
    """

    data = await bot.neo4j.cypher(
        r"""MATCH (u:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id})
        CALL gds.alpha.shortestPath.deltaStepping.stream({
            startNode: u,
            nodeProjection: 'FamilyTreeMember',
            relationshipProjection: {
                MARRIED_TO: {type: 'MARRIED_TO', orientation: 'NATURAL'},
                PARENT_OF: {type: 'PARENT_OF', orientation: 'NATURAL'}
            },
            delta: 1.0
        }) YIELD nodeId, distance
        WHERE distance < gds.util.infinity()
        RETURN gds.util.asNode(nodeId), distance""",
        user_id=user.id, guild_id=guild_id
    )
    matches = data['results'][0]['data']
    return matches


async def get_family_size(bot, user) -> int:
    """
    A cypher returning the size of a user's family.
    """

    return len(await get_all_family_member_nodes(bot, user))


async def get_blood_family_size(bot, user) -> int:
    """
    A cypher returning the size of a user's family when only considering blood relatives.
    """

    return len(await get_blood_family_member_nodes(bot, user))


async def get_relationship(bot, user, user2, guild_id:int=0) -> typing.Optional[typing.List[str]]:
    """
    A cypher that will return a list of MARRIED_TO, CHILD_OF, and PARENT_OF between two users
    If there's no relationship, the value None will be returned.
    """

    formatable_string = "(:FamilyTreeMember {{user_id: {0}, guild_id: {1}}})"
    tree_member_nodes = []
    uids = []
    data = await is_related(user, user2, guild_id)
    if not data:
        return None

    # Create all the nodes to match
    for row in data:
        user_id = row['row'][0]['user_id']
        tree_member_nodes.append(formatable_string.format(user_id, guild_id))

    # Create the cypher
    cypher = "MATCH "
    for tree_member in tree_member_nodes:
        cypher += tree_member
        if tree_member == tree_member_nodes[-1]:
            continue
        uids.append(get_random_string())
        cypher += f"-[{uids[-1]}]->"
    typed_uids = [f"type({i})" for i in uids]
    cypher += f" RETURN {', '.join(typed_uids)}"
    data = await bot.neo4j.cypher(cypher)

    # And this is the actual result
    matches = data['results'][0]['data'][0]['row']
    return matches


class FamilyMemberLock(object):

    def __init__(self, bot, *family_members, guild_id:int=None):
        if guild_id is None:
            raise TypeError("guild_id cannot be None")
        self.bot = bot
        self.family_members = family_members
        self.guild_id = guild_id

    async def __aenter__(self):
        await self.lock()
        return self

    async def lock(self):
        for user in self.family_members:
            if await is_family_pending_proposal(self.bot, user, self.guild_id):
                raise commands.CommandError(f"The family of {user.mention} has a pending proposal already.")
        for user in self.family_members:
            await self.bot.neo4j.cypher(
                r"""MATCH (u:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id}) SET u.pending_proposal=true""",
                user_id=user.id, guild_id=self.guild_id
            )

    async def __aexit__(self, exc_type, exc, tb):
        await self.unlock()

    async def unlock(self):
        for user in self.family_members:
            await self.bot.neo4j.cypher(
                r"""MATCH (u:FamilyTreeMember {user_id: $user_id, guild_id: $guild_id}) SET u.pending_proposal=false""",
                user_id=user.id, guild_id=self.guild_id
            )
