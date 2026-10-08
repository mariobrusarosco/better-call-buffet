from enum import Enum

MAX_TAGS_PER_ENTITY = 20


class TagSort(str, Enum):
    DISPLAY_ORDER = "display_order"
    USAGE = "usage"


MAX_TAG_LIST_LIMIT = 100
