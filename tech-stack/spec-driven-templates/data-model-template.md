# Data Model: {{TITLE}}

**Spec ID**: `{{SPEC_ID}}` | **Phase**: 1 (design)
**Date**: {{DATE}}

## Entities

### [EntityName]

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, indexed | Auto-generated |
| [field] | [type] | [constraints] | [notes] |

**Relationships**:
- [Entity] → [Entity]: [one-to-many / many-to-many]

## Schema (SQL or equivalent)

```sql
-- [DDL for entities above]
```

## Migrations

- [ ] [Migration 001: Create initial schema]
- [ ] [Migration 002: Add indexes]

## Validation Rules

- [Field] must be [constraint]
- [Entity] requires [related entity] to exist

<!--
  aiZee GATES:
  - Use parameterized queries [SEC-02]
  - Whitelist $fillable [SEC-03]
  - No raw SQL interpolation
-->
