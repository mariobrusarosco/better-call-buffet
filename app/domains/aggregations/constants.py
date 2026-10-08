from enum import Enum


class AggregationConditionOperator(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


MAX_AGGREGATION_DEPTH = 8
MAX_NODES_PER_VIEW = 100
