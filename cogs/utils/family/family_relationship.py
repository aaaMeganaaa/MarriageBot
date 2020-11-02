from .relationship_type import RelationshipType


class FamilyRelationship(object):
    """
    A helper object dataclass for cypher outputs to store two users and their relationship.
    """

    __slots__ = ('user', 'user_name', 'relationship', 'user2', 'user2_name',)

    def __init__(self, user:int, user_name:str, relationship:RelationshipType, user2:int, user2_name:str):
        self.user = user
        self.user_name = user_name
        self.relationship = relationship
        self.user2 = user2
        self.user2_name = user2_name

    def __eq__(self, other):
        return all([
            isinstance(other, self.__class__),
            self.user == other.user,
            self.relationship == other.relationship,
            self.user2 == other.user2
        ])
