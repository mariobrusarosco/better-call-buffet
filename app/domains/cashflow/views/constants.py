from enum import Enum

MAX_VIEW_NAME_LENGTH = 120
MAX_GROUP_NAME_LENGTH = 120
# Groups and sub-groups together.
MAX_GROUPS_PER_VIEW = 50
MAX_TAGS_PER_GROUP = 20


class GroupMatch(str, Enum):
    """How a group that holds tags matches expenses. Groups that hold
    sub-groups have no match (NULL)."""

    ANY = "any"  # at least one of the group's tags
    ALL = "all"  # every one of the group's tags
