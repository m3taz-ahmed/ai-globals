# aiZee MCP API Reference

**Version:** 5.3.0
**Transport:** stdio
**Server name:** `aizee`

## Overview

The aiZee MCP server exposes tools and resources for:
- Memory search and ingestion
- Workflow execution
- Policy and budget governance
- Context discovery (rules, skills, tech-stack, changelog)

## Tools

### Memory Tools

#### `search_memory`
Search the memory store by keyword.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `kind` | string | No | None | Filter by memory kind |
| `limit` | int | No | 20 | Max results (1-100) |

**Returns:** JSON array of matching memories with `id`, `kind`, `source`, `content`.

#### `search_memory_vector`
Search memory by vector similarity.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `k` | int | No | 5 | Number of results (1-100) |
| `kind` | string | No | None | Filter by kind |

**Returns:** JSON array with similarity scores.

#### `query_context`
Hybrid FTS + vector search across rules, tech-stack, workflows, and skills.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `k` | int | No | 5 | Results per mode (1-100) |
| `kind` | string | No | None | Filter by kind |

**Returns:** JSON array with `fts` and `vector` flags.

#### `ingest_memory`
Ingest rules, tech-stack, workflows, skills, and AGENTS.md into memory.

**Returns:** `{"ingested": <count>}`

#### `get_related_memories`
Get memories related to a given memory ID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mem_id` | string | Yes | - | Memory ID |
| `relation` | string | No | None | Relation type filter |

**Returns:** JSON array of related memories.

#### `add_memory`
Add a new memory to the store.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `kind` | string | Yes | - | `factual`, `semantic`, or `episodic` |
| `content` | string | Yes | - | Memory content |
| `source` | string | Yes | - | Source identifier |

**Returns:** `{"ok": true, "id": "<uuid>"}`

#### `invalidate_memory`
Deprecate a memory by ID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Memory ID |

**Returns:** `{"ok": true, "id": "<id>"}`

#### `build_schema_graph`
Build a knowledge graph from a SQLite database schema.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `db_path` | string | Yes | - | Database path (relative to root) |

**Returns:** Graph summary with node and edge counts.

### Workflow Tools

#### `query_rules`
Query rules by keyword with context filtering.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `context` | object | No | None | Context for frontmatter matching |

**Returns:** JSON array of matching rules.

#### `run_workflow`
Run a workflow by ID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Workflow ID (file stem) |
| `context` | object | No | None | Workflow context |

**Returns:** Workflow execution result.

#### `list_rules`
List available rule files.

**Returns:** JSON array of `{id, file}`.

#### `get_rule`
Get a rule file by stem ID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Rule file stem |

**Returns:** `{exists, path, content}` or `{exists: false}`.

#### `list_workflows`
List available workflow files.

**Returns:** JSON array of `{id, file}`.

#### `get_workflow`
Get a workflow file by stem ID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Workflow file stem |

**Returns:** `{exists, path, content}` or `{exists: false}`.

#### `compile_rule_files`
Compile rule/skill/workflow markdown into Rule IR.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `globs` | array | No | None | File globs to compile |

**Returns:** JSON array of compiled rules.

#### `run_mcp_plan`
Execute a multi-step plan across MCP tools.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `steps` | array | Yes | - | List of step definitions |

**Returns:** Execution results per step.

### Policy Tools

#### `check_policy`
Check if an action is allowed by policy and budget.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | Yes | - | Action type |
| `args` | object | No | None | Action arguments |

**Returns:** Policy decision with `ok`, `decision`, `budget`.

#### `analyze_budget`
Analyze current token and cost consumption.

**Returns:** Budget usage and configuration.

#### `run_guardian_check`
Evaluate a tool request against guardian rules.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tool` | string | Yes | - | Tool name |
| `attributes` | object | No | None | Tool attributes |

**Returns:** Guardian decision with `status`, `rule`, `reason`.

#### `get_metrics`
Return Prometheus-compatible metrics.

**Returns:** Prometheus exposition text.

#### `get_os_status`
Return the runtime kernel status.

**Returns:** JSON with `version`, `personas`, `workflows`, `budgets`, `rules`.

#### `list_capabilities`
List active sovereign capabilities.

**Returns:** JSON array of capabilities.

#### `lint_python`
Lint Python code using the Astryx AST linter.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `code` | string | Yes | - | Python code to lint |
| `max_lines` | int | No | 50 | Max lines per function |
| `max_params` | int | No | 7 | Max params per function |

**Returns:** `{ok, findings}` array.

### Context Tools

#### `get_tech_stack`
Get the tech-stack file for a package version.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pkg` | string | Yes | - | Package name |
| `ver` | string | Yes | - | Version string |

**Returns:** `{exists, path, content}` or `{exists: false}`.

#### `search_skills`
Search available skills by keyword.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `limit` | int | No | 20 | Max results |

**Returns:** JSON array of `{name, file, description}`.

#### `get_changelog`
Return the changelog.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `section` | string | No | `unreleased` | `unreleased`, `latest`, or `full` |
| `limit` | int | No | 50 | Max content length |

**Returns:** `{ok, section, content}`.

#### `get_active_context`
Return the ACTIVE_CONTEXT.md handoff file.

**Returns:** `{ok, content}`.

## Resources

### `rules://{id}`
Get a rule file by stem ID as a resource.

### `workflows://{id}`
Get a workflow file by stem ID as a resource.

### `os://AGENTS`
Get the AGENTS.md file content.

## Error Handling

All tools return JSON with:
- `{"ok": true, ...}` on success
- `{"ok": false, "error": "<message>"}` on failure

Input validation rejects:
- Path traversal (`..`, `\\`, `//`)
- Control characters
- Names longer than 128 characters
- Queries longer than 100,000 characters
- Results exceeding 100 items
