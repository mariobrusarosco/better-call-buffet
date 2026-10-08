from enum import Enum


class TagSelectionMode(str, Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"


MAX_TAGS_PER_ENTITY = 20
