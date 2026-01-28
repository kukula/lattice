"""Tests for schema models."""

import pytest
from pydantic import ValidationError

from lattice.schema.models import (
    Attribute,
    Entity,
    LatticeModel,
    Relationship,
    State,
    Transition,
)


class TestAttribute:
    def test_basic_attribute(self):
        attr = Attribute(name="email", type="string")
        assert attr.name == "email"
        assert attr.type == "string"
        assert attr.unique is False
        assert attr.optional is False

    def test_attribute_with_options(self):
        attr = Attribute(
            name="count",
            type="integer",
            min=0,
            max=100,
            unique=True,
        )
        assert attr.min == 0
        assert attr.max == 100
        assert attr.unique is True


class TestState:
    def test_basic_state(self):
        state = State(name="pending")
        assert state.name == "pending"
        assert state.initial is False
        assert state.terminal is False

    def test_initial_state(self):
        state = State(name="draft", initial=True)
        assert state.initial is True

    def test_terminal_state(self):
        state = State(name="completed", terminal=True)
        assert state.terminal is True


class TestTransition:
    def test_single_from_state(self):
        # Test that single from state is normalized to list
        data = {"from": "draft", "to": "published"}
        transition = Transition.model_validate(data)
        assert transition.from_states == ["draft"]
        assert transition.to == "published"

    def test_multiple_from_states(self):
        data = {"from": ["draft", "review"], "to": "published"}
        transition = Transition.model_validate(data)
        assert transition.from_states == ["draft", "review"]

    def test_transition_with_trigger(self):
        data = {"from": "pending", "to": "active", "trigger": "user.activate"}
        transition = Transition.model_validate(data)
        assert transition.trigger == "user.activate"

    def test_transition_with_requires(self):
        data = {
            "from": "pending",
            "to": "active",
            "requires": ["user.is_verified", "account.is_funded"],
        }
        transition = Transition.model_validate(data)
        assert len(transition.requires) == 2


class TestEntity:
    def test_shorthand_belongs_to(self):
        data = {
            "belongs_to": "User",
            "attributes": [{"name": "title", "type": "string"}],
        }
        entity = Entity.model_validate(data)
        assert len(entity.relationships) == 1
        assert entity.relationships[0].type == "belongs_to"
        assert entity.relationships[0].target == "User"

    def test_shorthand_has_many(self):
        data = {
            "has_many": ["Post", "Comment"],
            "attributes": [],
        }
        entity = Entity.model_validate(data)
        assert len(entity.relationships) == 2
        targets = [r.target for r in entity.relationships]
        assert "Post" in targets
        assert "Comment" in targets

    def test_mixed_relationships(self):
        data = {
            "belongs_to": "User",
            "has_many": "Comment",
            "relationships": [{"type": "depends_on", "target": "Config"}],
        }
        entity = Entity.model_validate(data)
        assert len(entity.relationships) == 3

    def test_state_normalization_from_strings(self):
        data = {
            "states": ["draft", "published", "archived"],
        }
        entity = Entity.model_validate(data)
        assert len(entity.states) == 3
        assert entity.states[0].name == "draft"

    def test_invariant_normalization_from_strings(self):
        data = {
            "invariants": ["Must be positive", "Cannot be null"],
        }
        entity = Entity.model_validate(data)
        assert len(entity.invariants) == 2
        assert entity.invariants[0].description == "Must be positive"


class TestLatticeModel:
    def test_entity_names_set(self):
        data = {
            "entities": {
                "User": {"attributes": [{"name": "email", "type": "string"}]},
                "Post": {"belongs_to": "User"},
            }
        }
        model = LatticeModel.model_validate(data)
        assert model.entities["User"].name == "User"
        assert model.entities["Post"].name == "Post"

    def test_get_entity(self):
        data = {
            "entities": {
                "User": {"attributes": []},
            }
        }
        model = LatticeModel.model_validate(data)
        assert model.get_entity("User") is not None
        assert model.get_entity("NonExistent") is None

    def test_get_all_entity_names(self):
        data = {
            "entities": {
                "User": {},
                "Post": {},
                "Comment": {},
            }
        }
        model = LatticeModel.model_validate(data)
        names = model.get_all_entity_names()
        assert set(names) == {"User", "Post", "Comment"}

    def test_system_invariants_normalization(self):
        data = {
            "entities": {},
            "system_invariants": [
                "Global constraint 1",
                {"description": "Global constraint 2", "formal": "x > 0"},
            ],
        }
        model = LatticeModel.model_validate(data)
        assert len(model.system_invariants) == 2
        assert model.system_invariants[0].scope == "system"
        assert model.system_invariants[1].scope == "system"
