import asyncio

from .relationship_type import RelationshipType


class FamilyMemberDotGenerator(object):
    """
    A helper class for the generation of DOT code from a family member object.
    """

    @staticmethod
    async def join_married_users(user_rank:list) -> str:
        """
        Join two married node users together.
        """

        added_relationships = set()
        added_marriages = set()
        output_string = "{rank=same;"
        for user in user_rank:
            partners = sorted(user.partners + [user])
            for index, p in enumerate(partners):
                try:
                    next_p = partners[index + 1]
                except IndexError:
                    continue
                relationship_string = p.get_relationship_string(next_p)
                this_marriage = tuple(sorted((p, next_p,)))
                if relationship_string not in added_relationships and this_marriage not in added_marriages:
                    output_string += f"{p.user_id} -> {relationship_string} -> {next_p.user_id};"
                    output_string += f"""{relationship_string}[shape=circle, label="", height=0.001, width=0.001];"""
                    added_relationships.add(relationship_string)
                    added_marriages.add(this_marriage)
                    added_marriages.add(tuple(sorted((user, p,))))
                    added_marriages.add(tuple(sorted((user, next_p,))))
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
            output_string += f"{user.user_id} -> h{user.user_id};"
        return output_string

    @staticmethod
    async def join_children_to_child_handler(user_rank:list) -> str:
        """
        Join a child handler node to a list of children.
        """

        output_string = ""
        added_relationships = []
        for user in user_rank:
            for child in user.children:
                output_string += f"h{user.user_id} -> {child.user_id};"
            if user.children and user._relationship_string not in added_relationships:
                output_string += f"""h{user.user_id}[shape=circle, label="", height=0.001, width=0.001];"""
                added_relationships.append(user._relationship_string)
        return output_string

    @classmethod
    async def expand_downwards_to_dot(cls, root_user) -> str:
        """
        Expand this tree downwards into a dot script.
        """

        added_users = 0
        output_string = (
            """digraph{rankdir="LR";"""
            """node [shape=box, fontcolor="#FFFFFF", color="#000000", fillcolor="#000000", style=filled];"""
            """edge [dir=none, color="#000000"];"""
        )

        # Loop through every user and append their partners
        this_rank_of_users = [root_user]
        for user in this_rank_of_users.copy():
            for p in user.partners:
                if p not in this_rank_of_users:
                    this_rank_of_users.append(p)

        # Add these users to the output string
        while this_rank_of_users:

            # Let's make sure this is in the right order
            this_rank_of_users.sort()

            # Add every user and user label
            for user in this_rank_of_users:
                output_string += f"""{user.user_id}[label="{user.name}"];"""
                added_users += 1

            gathered_strings = await asyncio.gather(
                cls.join_married_users(this_rank_of_users),
                cls.join_parents_to_child_handler(this_rank_of_users),
                cls.join_children_to_child_handler(this_rank_of_users),
            )
            # gathered_strings = await asyncio.wait_for(gathered_methods, timeout=None)
            married_users_string, parents_to_child_handler_string, child_handler_to_child_string = gathered_strings
            output_string += married_users_string + parents_to_child_handler_string + child_handler_to_child_string

            # Change the list of users to be the current rank's children and their partners
            old_rank_of_users = this_rank_of_users.copy()
            this_rank_of_users = []
            [this_rank_of_users.extend(i.children) for i in old_rank_of_users]
            for user in this_rank_of_users.copy():
                for p in user.partners:
                    this_rank_of_users.append(p)

        # Return stuff
        output_string += "}"
        return output_string.replace("{rank=same;}", ""), added_users


class FamilyMember(object):
    """
    An object to hold a given node from the database including all of its relationships.
    """

    __slots__ = ('user_id', '_name', 'parent', 'children', '_partners', '_relationship_string',)

    def __init__(self, user_id:int):
        self.user_id = user_id
        self._name = None
        self.parent = None
        self.children = []
        self._partners = []
        self._relationship_string = None

    @property
    def partners(self):
        # return list(sorted(self._partners, key=lambda i: i.user_id))
        return self._partners

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.user_id == other.user_id

    def __gt__(self, other):
        return self.user_id > other.user_id

    def __lt__(self, other):
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
                    node.partners.append(new_object)
                    new_object.partners.append(node)
                family_objects[relationship.user2] = new_object

            # Add children
            elif relationship.relationship == RelationshipType.PARENT_OF:
                new_object = family_objects.get(relationship.user2, cls(relationship.user2))
                new_object._name = relationship.user2_name
                if new_object not in node.children:
                    node.children.append(new_object)
                    new_object.parent = node
                family_objects[relationship.user2] = new_object

        # Return the root user
        return family_objects.get(root_user_id or list(family_objects.keys())[0])
