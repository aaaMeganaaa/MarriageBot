import enum


class RelationshipType(enum.Enum):
    """
    The different valid kinds of relationship.
    """

    MARRIED_TO = enum.auto()
    PARENT_OF = enum.auto()
    CHILD_OF = enum.auto()
