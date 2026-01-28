"""Pydantic models for Lattice schema."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Attribute(BaseModel):
    """An attribute of an entity."""

    name: str
    type: str
    unique: bool = False
    optional: bool = False
    min: int | float | None = None
    max: int | float | None = None
    default: str | int | float | bool | None = None
    description: str | None = None


class State(BaseModel):
    """A state in an entity's state machine."""

    name: str
    initial: bool = False
    terminal: bool = False


class Condition(BaseModel):
    """A condition/guard for transitions."""

    expression: str


class Effect(BaseModel):
    """An effect/side-effect of a transition."""

    expression: str


class Transition(BaseModel):
    """A transition between states."""

    from_states: list[str] = Field(alias="from")
    to: str
    trigger: str | None = None
    requires: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_from_states(cls, data: dict) -> dict:
        """Normalize from to always be a list."""
        if isinstance(data, dict):
            from_val = data.get("from")
            if from_val is not None and not isinstance(from_val, list):
                data["from"] = [from_val]
        return data


class Relationship(BaseModel):
    """A relationship between entities."""

    type: Literal["belongs_to", "has_many", "has_one", "depends_on"]
    target: str
    conditions: list[str] = Field(default_factory=list)


class Computed(BaseModel):
    """A computed property."""

    name: str
    formula: str


class Invariant(BaseModel):
    """An invariant/constraint that must hold."""

    description: str
    formal: str | None = None
    scope: Literal["entity", "system"] = "entity"


class Entity(BaseModel):
    """An entity in the model."""

    name: str = ""  # Will be set from the key
    attributes: list[Attribute] = Field(default_factory=list)
    states: list[State] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    computed: list[Computed] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    unclear: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_entity(cls, data: dict) -> dict:
        """Normalize shorthand relationship syntax and states."""
        if not isinstance(data, dict):
            return data

        # Normalize shorthand relationships (belongs_to: Target -> relationships list)
        relationships = data.get("relationships", [])
        if not isinstance(relationships, list):
            relationships = []

        # First, normalize items within the relationships list that use shorthand
        # e.g., {has_many: Post} -> {type: "has_many", target: "Post"}
        normalized_rels = []
        for rel in relationships:
            if isinstance(rel, dict):
                # Check if it's already normalized (has 'type' and 'target')
                if "type" in rel and "target" in rel:
                    normalized_rels.append(rel)
                else:
                    # Check for shorthand syntax
                    for rel_type in ["belongs_to", "has_many", "has_one", "depends_on"]:
                        if rel_type in rel:
                            target = rel[rel_type]
                            normalized_rels.append({"type": rel_type, "target": target})
                            break
            else:
                normalized_rels.append(rel)
        relationships = normalized_rels

        # Also handle top-level shorthand (belongs_to: Target at entity level)
        for rel_type in ["belongs_to", "has_many", "has_one", "depends_on"]:
            if rel_type in data:
                targets = data.pop(rel_type)
                if isinstance(targets, str):
                    targets = [targets]
                for target in targets:
                    relationships.append({"type": rel_type, "target": target})

        data["relationships"] = relationships

        # Normalize states from list of strings or dicts
        states = data.get("states", [])
        if states:
            normalized_states = []
            for state in states:
                if isinstance(state, str):
                    normalized_states.append({"name": state})
                else:
                    normalized_states.append(state)
            data["states"] = normalized_states

        # Normalize attributes from list of strings or dicts
        attributes = data.get("attributes", [])
        if attributes:
            normalized_attrs = []
            for attr in attributes:
                if isinstance(attr, str):
                    normalized_attrs.append({"name": attr, "type": "string"})
                else:
                    normalized_attrs.append(attr)
            data["attributes"] = normalized_attrs

        # Normalize invariants from list of strings or dicts
        invariants = data.get("invariants", [])
        if invariants:
            normalized_invariants = []
            for inv in invariants:
                if isinstance(inv, str):
                    normalized_invariants.append({"description": inv})
                else:
                    normalized_invariants.append(inv)
            data["invariants"] = normalized_invariants

        # Normalize computed from list of strings or dicts
        computed = data.get("computed", [])
        if computed:
            normalized_computed = []
            for comp in computed:
                if isinstance(comp, str):
                    normalized_computed.append({"name": comp, "formula": ""})
                else:
                    normalized_computed.append(comp)
            data["computed"] = normalized_computed

        return data


class LatticeModel(BaseModel):
    """Root model for a Lattice YAML file."""

    entities: dict[str, Entity] = Field(default_factory=dict)
    system_invariants: list[Invariant] = Field(default_factory=list)
    temporal_rules: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_model(cls, data: dict) -> dict:
        """Normalize the model data."""
        if not isinstance(data, dict):
            return data

        # Set entity names from keys
        entities = data.get("entities", {})
        if isinstance(entities, dict):
            for name, entity_data in entities.items():
                if isinstance(entity_data, dict):
                    entity_data["name"] = name

        # Normalize system_invariants from list of strings or dicts
        system_invariants = data.get("system_invariants", [])
        if system_invariants:
            normalized = []
            for inv in system_invariants:
                if isinstance(inv, str):
                    normalized.append({"description": inv, "scope": "system"})
                else:
                    if isinstance(inv, dict):
                        inv["scope"] = "system"
                    normalized.append(inv)
            data["system_invariants"] = normalized

        return data

    def get_entity(self, name: str) -> Entity | None:
        """Get an entity by name."""
        return self.entities.get(name)

    def get_all_entity_names(self) -> list[str]:
        """Get all entity names."""
        return list(self.entities.keys())
