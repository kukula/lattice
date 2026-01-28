# Lattice: Self-Validating System Models

Working document for building an MVP of the graph-based intent modeling tool.

---


## Core Hypothesis to Test

A graph-based representation of system intent can:
1. Be authored by humans in a simple text format
2. Be read and modified by LLMs
3. Validate itself structurally without external tools
4. Surface semantic gaps via LLM analysis
5. Generate meaningful tests from invariants

MVP goal: prove this loop works for ONE bounded context (e.g., authorization or order state machine).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Human / LLM                          │
│                        │                                │
│                        ▼                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Text Format (YAML/DSL)                │   │
│  │         - human readable/writable                │   │
│  │         - LLM readable/writable                  │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                │
│                        ▼ parse                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Graph Storage                       │   │
│  │         - nodes, edges, properties               │   │
│  │         - queryable                              │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                │
│           ┌────────────┴────────────┐                  │
│           ▼                         ▼                  │
│  ┌─────────────────┐    ┌─────────────────────────┐   │
│  │   Structural    │    │      Semantic           │   │
│  │   Validation    │    │      Validation         │   │
│  │   (fast, local) │    │      (async, LLM)       │   │
│  └─────────────────┘    └─────────────────────────┘   │
│           │                         │                  │
│           └────────────┬────────────┘                  │
│                        ▼                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Feedback Layer                      │   │
│  │    - errors (structural)                         │   │
│  │    - warnings (semantic)                         │   │
│  │    - unclear markers                             │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                │
│                        ▼                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Test Generation                        │   │
│  │    - positive/negative/boundary cases            │   │
│  │    - derived from invariants                     │   │
│  └─────────────────────────────────────────────────┘   │
│                        │                                │
│                        ▼                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Code Generation / LLM Impl             │   │
│  │    - constrained by graph + tests                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack Candidates

### Graph Storage

| Option | Pros | Cons |
|--------|------|------|
| **SQLite + custom schema** | Zero deps, portable, SQL queryable | Manual graph traversal |
| **In-memory (Python dicts/networkx)** | Simple, fast iteration | No persistence story |
| **JSON files + jq** | Dead simple, version control friendly | Validation is custom |
| **DuckDB** | SQLite-like but better analytics | Overkill for MVP |
| **EdgeDB** | Graph-native, nice query language | Another dependency |

**MVP recommendation:** Start with YAML files → parsed into Python dicts/networkx for validation → later add SQLite if persistence matters.

### Text Format

Options:
1. **Pure YAML** - familiar, tooling exists, but verbose
2. **Custom DSL** - terse, but need to write parser
3. **Markdown + frontmatter** - human friendly, but parsing is annoying
4. **Structured comments in code** - close to implementation, but coupled

**MVP recommendation:** YAML with conventions. Define a schema, validate against it. Iterate toward DSL if YAML friction is high.

### Validation Engine

- **Structural:** Python + networkx/custom graph traversal
- **Semantic:** LLM API calls (Claude) with graph context
- **Schema validation:** Pydantic or JSON Schema

### Interface

Options for MVP:
1. **CLI tool** - `intent validate model.yaml`, `intent generate-tests model.yaml`
2. **LSP server** - real-time validation in editor
3. **Web UI** - visual graph + inline warnings
4. **Jupyter notebook** - exploratory, good for demos

**MVP recommendation:** CLI first. Proves the core loop. Web UI later for visualization.

---

## Data Model

### Node Types

```python
class Entity:
    name: str
    attributes: list[Attribute]
    states: list[State] | None  # if stateful
    relationships: list[Relationship]
    invariants: list[Invariant]
    unclear: list[str]  # explicit ambiguity markers

class State:
    name: str
    terminal: bool = False
    
class Transition:
    from_state: str | list[str]
    to_state: str
    trigger: str | None  # event that causes it
    requires: list[Condition]  # guards
    
class Relationship:
    type: Literal["belongs_to", "has_many", "has_one", "depends_on"]
    target: str
    conditions: list[Condition] | None

class Invariant:
    description: str
    formal: str | None  # optional formal expression
    scope: Literal["entity", "system"]

class Condition:
    expression: str  # e.g., "line_items.count > 0"
    # TODO: define expression grammar
```

### Edge Types

- `belongs_to` / `has_many` / `has_one` - entity relationships
- `transition` - state machine edges
- `requires` - dependency/precondition
- `produces` - causality (action → effect)
- `authorizes` - permission paths

### Meta Schema (Graph Validates Itself)

```yaml
_meta:
  rules:
    - every Entity must have at least one relationship OR be marked standalone
    - every State must be reachable from initial state
    - every Transition.to_state must reference a defined State
    - every Relationship.target must reference a defined Entity
    - no two Invariants can contradict (detected semantically)
```

---

## Structural Validation Rules

Implement as functions that take the graph and return `list[Error | Warning]`:

```python
def check_orphan_entities(graph) -> list[Warning]:
    """Entities with no relationships"""
    
def check_unreachable_states(graph) -> list[Error]:
    """States that cannot be reached from initial"""
    
def check_terminal_states(graph) -> list[Warning]:
    """States with no outbound transitions, not marked terminal"""
    
def check_reference_integrity(graph) -> list[Error]:
    """All references resolve to defined nodes"""
    
def check_transition_completeness(graph) -> list[Warning]:
    """State machine has gaps - e.g., no transition from X for event Y"""
    
def check_duplicate_definitions(graph) -> list[Error]:
    """Same node defined twice with different properties"""
    
def check_cycle_detection(graph) -> list[Warning]:
    """Circular dependencies that may cause issues"""
```

---

## Semantic Validation Prompts

LLM receives the graph (or relevant subgraph) and answers:

```
Given this system model:

{graph_yaml}

Identify:
1. Potential contradictions between invariants or rules
2. Missing transitions or relationships that seem implied
3. Ambiguities that should be clarified
4. Edge cases that aren't handled

Format as:
- CONTRADICTION: {description}
- MISSING: {description}  
- AMBIGUOUS: {description}
- EDGE_CASE: {description}
```

Parse response, attach to relevant nodes as warnings.

---

## Test Generation Strategy

### From State Machines

```python
def generate_state_machine_tests(entity):
    tests = []
    
    # Positive: each valid transition works
    for t in entity.transitions:
        tests.append(PositiveTest(
            name=f"{entity.name}_can_transition_{t.from_state}_to_{t.to_state}",
            setup=f"entity in state {t.from_state}, {t.requires} satisfied",
            action=f"trigger {t.trigger or 'transition'}",
            expected=f"entity in state {t.to_state}"
        ))
    
    # Negative: invalid transitions fail
    for state in entity.states:
        valid_targets = [t.to_state for t in entity.transitions if t.from_state == state.name]
        invalid_targets = [s.name for s in entity.states if s.name not in valid_targets and s.name != state.name]
        for invalid in invalid_targets:
            tests.append(NegativeTest(
                name=f"{entity.name}_cannot_transition_{state.name}_to_{invalid}",
                setup=f"entity in state {state.name}",
                action=f"attempt transition to {invalid}",
                expected="rejected"
            ))
    
    # Boundary: guards not satisfied
    for t in entity.transitions:
        if t.requires:
            tests.append(BoundaryTest(
                name=f"{entity.name}_transition_{t.from_state}_to_{t.to_state}_blocked_without_requirements",
                setup=f"entity in state {t.from_state}, {t.requires} NOT satisfied",
                action=f"trigger {t.trigger or 'transition'}",
                expected="rejected or blocked"
            ))
    
    return tests
```

### From Authorization Invariants

```python
def generate_auth_tests(invariant):
    # Parse invariant like "User can only access own Orders"
    # Generate:
    # - Positive: user accesses own order → success
    # - Negative: user accesses other's order → denied
    # - Boundary: user's order transferred to other user → access revoked
```

### Output Format

Generate as:
- pytest stubs (Python)
- RSpec stubs (Ruby)
- Plain text scenarios (for LLM to implement)

---

## MVP Milestones

### Week 1: Parse and Validate Structure

- [ ] Define YAML schema for entities, states, transitions, relationships
- [ ] Parser: YAML → internal graph representation
- [ ] Implement 3 structural validators (orphans, unreachable states, reference integrity)
- [ ] CLI: `intent validate model.yaml` → prints errors/warnings

### Week 2: Semantic Validation

- [ ] Integrate Claude API
- [ ] Prompt engineering for contradiction/gap detection
- [ ] Parse LLM response into structured warnings
- [ ] Attach warnings to nodes
- [ ] CLI: `intent analyze model.yaml` → prints semantic warnings

### Week 3: Test Generation

- [ ] State machine → test cases (positive/negative/boundary)
- [ ] Output as pytest stubs
- [ ] CLI: `intent generate-tests model.yaml` → writes test files

### Week 4: End-to-End Demo

- [ ] Model one real bounded context (e.g., order lifecycle)
- [ ] Full loop: model → validate → generate tests → LLM implements → tests pass
- [ ] Document the experience, pain points, surprises

---

## Example Model (Order Lifecycle)

```yaml
# order_model.yaml

entities:
  Customer:
    attributes:
      - name: email
        type: string
        unique: true
      - name: payment_methods
        type: list[PaymentMethod]
    relationships:
      - has_many: Order

  Order:
    belongs_to: Customer
    has_many: LineItem
    
    states:
      - name: draft
        initial: true
      - name: submitted
      - name: paid
      - name: shipped
      - name: delivered
        terminal: true
      - name: cancelled
        terminal: true
    
    transitions:
      - from: draft
        to: submitted
        requires:
          - line_items.count > 0
      - from: submitted
        to: paid
        trigger: payment.success
      - from: submitted
        to: cancelled
        trigger: payment.failed
      - from: paid
        to: shipped
        requires:
          - inventory.reserved_for(order)
      - from: shipped
        to: delivered
        trigger: delivery.confirmed
      - from: [draft, submitted]
        to: cancelled
        trigger: customer.cancel
    
    invariants:
      - description: "Order total equals sum of line item prices"
        formal: "order.total == sum(line_items.map(li => li.price * li.quantity))"
      - description: "Cannot ship without payment"
      - description: "Customer can only cancel before shipment"
    
    unclear:
      - "What if partial inventory available? Partial ship or block?"
      - "Refund flow after payment but before ship?"

  LineItem:
    belongs_to: Order
    belongs_to: Product
    attributes:
      - name: quantity
        type: integer
        min: 1
      - name: price_at_purchase
        type: decimal

  Product:
    attributes:
      - name: sku
        type: string
        unique: true
      - name: inventory_count
        type: integer
        min: 0
    
    invariants:
      - description: "Inventory cannot go negative"
        formal: "inventory_count >= 0"

invariants:
  - description: "A user can only view their own orders"
    scope: system
    formal: "forall o in Order: o.viewer == o.customer"
```

---

## Open Questions

1. **Expression language for conditions/invariants** - How formal? Custom DSL? Subset of Python? Plain English that LLM interprets?

2. **Versioning semantics** - How to handle model migrations? If a state is renamed, what happens to existing data?

3. **Multi-model composition** - How do separate bounded contexts reference each other? Import system?

4. **Confidence levels** - Should invariants have confidence? "Must hold" vs "should hold" vs "nice to have"?

5. **Escape hatch syntax** - How to mark "here be dragons" external systems cleanly?

6. **Visualization** - What's the minimal useful visual representation? State machine diagrams? Entity relationship diagrams? Both?

7. **Editor integration** - LSP server for real-time validation? VS Code extension? Web-based editor?

---

## References

- Alloy (formal modeling language) - https://alloytools.org/
- TLA+ (temporal logic) - https://lamport.azurewebsites.net/tla/tla.html
- Domain-Driven Design (bounded contexts, aggregates)
- Model-Based Systems Engineering (SysML, AADL)
- Statecharts (Harel) - hierarchical state machines
- Design by Contract (Eiffel, DbC)

---

## Notes / Scratchpad

*Use this space for random thoughts during implementation*

- 
- 
- 
