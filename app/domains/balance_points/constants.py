from enum import Enum

class TimelineStatus(str, Enum):
    CURRENT = "current"
    UPDATING = "updating"
    FAILED = "failed"   