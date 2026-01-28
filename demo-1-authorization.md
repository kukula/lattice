# Demo 1: Authorization & Access Control

## What This Demo Shows

- **Permission path validation** - can User reach Action through valid Role/Permission chain?
- **Gap detection** - actions with no permission path, orphan permissions
- **Query capabilities** - "who can do X?", "what can user Y do?"
- **Contradiction detection** - conflicting allow/deny rules

---

## The Model

```yaml
# authorization_model.yaml

entities:
  User:
    attributes:
      - name: email
        type: string
        unique: true
      - name: status
        type: enum[active, suspended, deleted]
    relationships:
      - has_many: RoleAssignment
    
    invariants:
      - description: "Suspended users cannot perform any actions"
      - description: "Deleted users cannot log in"

  Role:
    attributes:
      - name: name
        type: string
        unique: true
      - name: description
        type: string
    relationships:
      - has_many: Permission
      - has_many: RoleAssignment
    
    invariants:
      - description: "Every role must have at least one permission"

  Permission:
    attributes:
      - name: name
        type: string
      - name: resource
        type: string
      - name: action
        type: enum[create, read, update, delete, execute]
    relationships:
      - belongs_to: Role

  RoleAssignment:
    belongs_to: User
    belongs_to: Role
    attributes:
      - name: granted_at
        type: datetime
      - name: expires_at
        type: datetime
        optional: true
      - name: granted_by
        type: reference[User]

  Resource:
    attributes:
      - name: type
        type: string
      - name: owner
        type: reference[User]
    
    invariants:
      - description: "Owner always has full access to their resources"

roles:
  admin:
    permissions:
      - resource: "*"
        action: "*"
    
  editor:
    permissions:
      - resource: Document
        action: [create, read, update]
      - resource: Comment
        action: [create, read, update, delete]
  
  viewer:
    permissions:
      - resource: Document
        action: read
      - resource: Comment
        action: read

  billing_admin:
    permissions:
      - resource: Invoice
        action: [create, read, update]
      - resource: Subscription
        action: [read, update]

authorization_rules:
  - name: owner_access
    description: "Resource owner has full access"
    rule: "user == resource.owner => allow(*)"
  
  - name: role_based_access
    description: "Access granted through role permissions"
    rule: |
      user.roles.any(role => 
        role.permissions.any(p => 
          p.resource == resource.type && p.action == action
        )
      ) => allow(action)
  
  - name: suspended_block
    description: "Suspended users blocked from all actions"
    rule: "user.status == suspended => deny(*)"
    priority: high  # evaluated first

  - name: self_service
    description: "Users can always update their own profile"
    rule: "resource.type == UserProfile && resource.owner == user => allow(update)"

invariants:
  - description: "No permission path should allow suspended user to act"
    scope: system
  
  - description: "Admin role must exist and have at least one user"
    scope: system
  
  - description: "Every action on every resource must have at least one permission path"
    scope: system

unclear:
  - "Can a user have conflicting roles (e.g., editor + restricted_viewer)?"
  - "How to handle permission expiry mid-session?"
  - "Should role assignment require approval workflow?"
```

---

## Expected Structural Validation Output

```
$ intent validate authorization_model.yaml

ERRORS:
  (none)

WARNINGS:
  ⚠ Role 'viewer' has read-only permissions - intentional?
  ⚠ Permission 'Invoice.delete' not assigned to any role - orphan?
  ⚠ No role grants 'Subscription.create' - gap in permission coverage?
  
UNCLEAR (3 items):
  ? "Can a user have conflicting roles?"
  ? "How to handle permission expiry mid-session?"
  ? "Should role assignment require approval workflow?"
```

---

## Expected Semantic Validation Output

```
$ intent analyze authorization_model.yaml

POTENTIAL ISSUES:

CONTRADICTION:
  Rule 'owner_access' grants full access, but 'suspended_block' denies all.
  If owner is suspended, which wins?
  → Recommendation: Clarify priority or add explicit "suspended owner" rule.

MISSING:
  No permission path for 'Subscription.create'. 
  Who can create subscriptions?
  
AMBIGUOUS:
  'billing_admin' can update Subscription but not create.
  Is this intentional? Usually create/update are paired.

EDGE_CASE:
  User has role with expires_at in the past but RoleAssignment not deleted.
  Should access be denied? Currently not specified.
```

---

## Generated Test Cases

```python
# test_authorization.py (generated)

class TestRoleBasedAccess:
    """Positive cases: valid permission paths work"""
    
    def test_admin_can_access_any_resource(self):
        user = create_user(roles=["admin"])
        assert can_access(user, resource=any_document, action="delete")
    
    def test_editor_can_create_document(self):
        user = create_user(roles=["editor"])
        assert can_access(user, resource=Document, action="create")
    
    def test_viewer_can_read_document(self):
        user = create_user(roles=["viewer"])
        assert can_access(user, resource=Document, action="read")


class TestAccessDenied:
    """Negative cases: invalid paths are rejected"""
    
    def test_viewer_cannot_update_document(self):
        user = create_user(roles=["viewer"])
        assert not can_access(user, resource=Document, action="update")
    
    def test_editor_cannot_delete_document(self):
        user = create_user(roles=["editor"])
        assert not can_access(user, resource=Document, action="delete")
    
    def test_billing_admin_cannot_access_documents(self):
        user = create_user(roles=["billing_admin"])
        assert not can_access(user, resource=Document, action="read")


class TestSuspendedUsers:
    """Boundary cases: suspended status blocks all access"""
    
    def test_suspended_admin_cannot_access(self):
        user = create_user(roles=["admin"], status="suspended")
        assert not can_access(user, resource=any_resource, action="read")
    
    def test_suspended_owner_cannot_access_own_resource(self):
        user = create_user(status="suspended")
        resource = create_resource(owner=user)
        assert not can_access(user, resource=resource, action="read")


class TestOwnerAccess:
    """Owner override cases"""
    
    def test_owner_can_delete_own_resource_without_role(self):
        user = create_user(roles=[])  # no roles
        resource = create_resource(owner=user)
        assert can_access(user, resource=resource, action="delete")
    
    def test_non_owner_with_viewer_role_cannot_delete(self):
        owner = create_user()
        other = create_user(roles=["viewer"])
        resource = create_resource(owner=owner)
        assert not can_access(other, resource=resource, action="delete")


class TestRoleExpiry:
    """Boundary cases: temporal conditions"""
    
    def test_expired_role_denies_access(self):
        user = create_user(roles=["editor"], role_expires_at=yesterday)
        assert not can_access(user, resource=Document, action="create")
    
    def test_not_yet_active_role_denies_access(self):
        user = create_user(roles=["editor"], role_starts_at=tomorrow)
        assert not can_access(user, resource=Document, action="create")
```

---

## Query Examples

Once the graph exists, you can query it:

```
$ intent query authorization_model.yaml "who can delete Documents?"

Users with permission path to Document.delete:
  - Users with role: admin (direct)
  - Users who own the Document (via owner_access rule)

$ intent query authorization_model.yaml "what can a viewer do?"

Role 'viewer' permissions:
  - Document.read
  - Comment.read

$ intent query authorization_model.yaml "show all paths from User to Invoice.update"

Paths:
  1. User → RoleAssignment → Role(billing_admin) → Permission(Invoice.update)
  2. User → Resource(Invoice, owner=User) → owner_access rule
```

---

## What This Demo Validates

| Capability | Demonstrated |
|------------|--------------|
| Structural: orphan detection | ✓ Invoice.delete has no role |
| Structural: completeness | ✓ Subscription.create has no path |
| Semantic: contradiction | ✓ owner_access vs suspended_block conflict |
| Semantic: gaps | ✓ billing_admin can update but not create |
| Test generation: positive | ✓ valid permission paths work |
| Test generation: negative | ✓ invalid paths rejected |
| Test generation: boundary | ✓ suspended users, expiry edge cases |
| Queryable graph | ✓ "who can do X" queries |
