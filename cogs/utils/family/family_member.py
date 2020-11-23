import asyncio

from .relationship_type import RelationshipType
from .utils import get_random_string


import logging
logger = logging.getLogger("vflbotutils")


class FamilyMemberDotGenerator(object):
    """
    A helper class for the generation of DOT code from a family member object.
    """

    @staticmethod
    def add_user_partners(user_objects:list) -> list:
        """
        Loop and add all the partners for a given generation to the user objects list/
        """

        offset = 0
        try:
            while True:
                if not user_objects[offset:]:
                    break
                for p in user_objects[offset:]:
                    offset = len(user_objects)
                    user_objects.extend([i for i in p.partners if i not in user_objects])
        except IndexError:
            pass
        return user_objects

    @classmethod
    async def join_married_users(cls, user_rank:list) -> str:
        """
        Join two married node users together.
        """

        # Set up dupe trackers
        added_users = set()

        # Start our data
        output_string = "{rank=same;"

        # Go through users in this generation
        # previous_user_from_rank = None
        for user in user_rank:

            # See if we can extend our partner list to EVERYONE in that section
            partners = [i for i in cls.add_user_partners([user]) if i not in added_users]
            partners.sort()

            # Add each user label
            for index, p in enumerate(partners):
                if index == 0:
                    user_line = f"""{p.user_id}[label="{p.name}",comment="FIRST"];"""
                else:
                    user_line = f"""{p.user_id}[label="{p.name}"];"""
                if user_line not in output_string:
                    output_string += user_line

            # Go through each of the partners
            for index, p in enumerate(partners):

                # Get the next one in the list so we can join them
                try:
                    next_p = partners[index + 1]
                except IndexError:
                    continue

                # Add the user and their marriage
                if index == 0:
                    output_string += f"{p.user_id} -> {next_p.user_id}"
                else:
                    output_string += f" -> {next_p.user_id}"

            # Say that we added the users
            if output_string[-1] != ";":
                output_string += ";"
            added_users.update(set(partners))

        # We done gamers
        output_string += "}"
        return output_string

    @staticmethod
    async def join_parents_to_child_handler(user_rank:list) -> str:
        """
        Join a parent/relationship node to a child handler node.
        """

        output_string = ""
        for user in user_rank:
            if not user.children:
                continue
            output_string += f"{user.user_id} -> h{user.user_id}[constraint=true];"
        return output_string

    @staticmethod
    async def join_children_to_child_handler(user_rank:list) -> str:
        """
        Join a child handler node to a list of children.
        """

        output_string = ""
        for user in user_rank:
            for index, child in enumerate(user.children):
                output_string += f"h{user.user_id} -> {child.user_id}[constraint=true];"
                # try:
                #     output_string += f"{child.user_id} -> {user.children[index + 1].user_id}[style=invis];"
                # except IndexError:
                #     pass
            invis_string = f"""h{user.user_id}[shape=circle,label="",height=0.0001,width=0.0001];"""
            if user.children and invis_string not in output_string:
                output_string += invis_string
        return output_string

    @classmethod
    async def expand_downwards_to_dot(cls, root_user) -> str:
        """
        Expand this tree downwards into a dot script.
        """

        added_users = 0
        output_string = (
            # """digraph{rankdir=LR;overlap=false;concentrate=true;ordering=out;"""
            """digraph{rankdir=LR;"""
            # """digraph{rankdir=TB;"""
            """node[shape=box,fontcolor="#FFFFFF",color="#000000",fillcolor="#000000",style=filled];"""
            """edge[dir=none,color="#000000"];"""
        )

        # Loop through every user and append their partners
        root_user._main = True
        this_rank_of_users = cls.add_user_partners([root_user])

        # Add these users to the output string
        while this_rank_of_users:

            # Let's make sure this is in the right order
            logger.info(this_rank_of_users)
            this_rank_of_users.sort()
            added_users += len(this_rank_of_users)

            gathered_strings = await asyncio.gather(
                cls.join_married_users(this_rank_of_users),
                cls.join_parents_to_child_handler(this_rank_of_users),
                cls.join_children_to_child_handler(this_rank_of_users),
            )
            married_users_string, parents_to_child_handler_string, child_handler_to_child_string = gathered_strings
            output_string += married_users_string + parents_to_child_handler_string + child_handler_to_child_string

            # Change the list of users to be the current rank's children and their partners
            old_rank_of_users = this_rank_of_users.copy()
            this_rank_of_users = []
            for i in old_rank_of_users:
                this_rank_of_users.extend(i.children)
            this_rank_of_users = cls.add_user_partners(this_rank_of_users)  # Change this_rank.. by reference

        # Return stuff
        output_string += "}"
        output_string = output_string.replace("{rank=same;}", "")
        output_string = output_string.replace(';', ';\n')
        return output_string, added_users


class FamilyMember(object):
    """
    An object to hold a given node from the database including all of its relationships.
    """

    __slots__ = ('user_id', '_name', 'parent', '_children', '_partners', '_relationship_string', '_main',)

    def __init__(self, user_id:int):
        self.user_id = user_id
        self._name = None
        self.parent = None
        self._children = []
        self._partners = []
        self._relationship_string = None
        self._main = False

    @property
    def children(self):
        return self._children.copy()

    @property
    def partners(self):
        return self._partners.copy()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.user_id == other.user_id

    def __gt__(self, other):
        if self._main:
            return True
        return self.user_id > other.user_id

    def __lt__(self, other):
        if self._main:
            return False
        return self.user_id < other.user_id

    def __hash__(self):
        # return f"FAMILY_MEMBER {self.user_id}"
        return self.user_id

    @property
    def relationship_string(self):
        if self._relationship_string:
            return self._relationship_string
        if self.partner:
            relationship_list = sorted([self.user_id, self.partner.user_id])
            self._relationship_string = f"r{relationship_list[1]}_{relationship_list[0]}"
        else:
            self._relationship_string = f"{self.user_id}"
        return self._relationship_string

    def get_relationship_string(self, other):
        if other is not None:
            relationship_list = sorted([self.user_id, other.user_id])
            self._relationship_string = f"r{relationship_list[1]}_{relationship_list[0]}"
        else:
            self._relationship_string = f"{self.user_id}"
        return self._relationship_string

    @property
    def name(self):
        return self._name or self.user_id

    @classmethod
    def get_family_from_cypher(cls, cypher_output:list, root_user_id:int=None):
        """
        Get a family member object via a cypher, adding that family's children/partners/etc to the base user.
        """

        # Make a place to store our family objects
        family_objects = {}

        # Go through each relationship in the cipher output
        for relationship in cypher_output:

            # Make sure our node exists
            node = family_objects.setdefault(relationship.user, cls(relationship.user))
            node._name = relationship.user_name

            # Add marriages
            if relationship.relationship == RelationshipType.MARRIED_TO:
                new_object = family_objects.get(relationship.user2, cls(relationship.user2))
                new_object._name = relationship.user2_name
                if new_object not in node.partners:
                    node._partners.append(new_object)
                    new_object._partners.append(node)
                family_objects[relationship.user2] = new_object

            # Add children
            elif relationship.relationship == RelationshipType.PARENT_OF:
                new_object = family_objects.get(relationship.user2, cls(relationship.user2))
                new_object._name = relationship.user2_name
                if new_object not in node.children:
                    node._children.append(new_object)
                    new_object.parent = node
                family_objects[relationship.user2] = new_object

        # Return the root user
        return family_objects.get(root_user_id or list(family_objects.keys())[0])
