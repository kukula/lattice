"""Node and edge type definitions for the model graph."""

from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in the model graph."""

    ENTITY = "entity"
    STATE = "state"
    ATTRIBUTE = "attribute"
    INVARIANT = "invariant"


class EdgeType(str, Enum):
    """Types of edges in the model graph."""

    # Entity relationships
    BELONGS_TO = "belongs_to"
    HAS_MANY = "has_many"
    HAS_ONE = "has_one"
    DEPENDS_ON = "depends_on"

    # State machine edges
    TRANSITION = "transition"

    # Structure edges
    HAS_STATE = "has_state"  # Entity -> State
    HAS_ATTRIBUTE = "has_attribute"  # Entity -> Attribute
    HAS_INVARIANT = "has_invariant"  # Entity -> Invariant
