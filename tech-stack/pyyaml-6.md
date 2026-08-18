[TECH] pyyaml-6
[OBJ] PyYAML 6.x parsing standards for aiZee rules/policies/workflows.
[RULES]
1. [REQ] `yaml.safe_load()` for untrusted YAML. NEVER `yaml.load()` without `Loader=SafeLoader`.
2. [REQ] `yaml.safe_dump()` for serialization. `default_flow_style=False` for readability.
3. [REQ] `yaml.YAMLError` caught at boundary. Re-raise as `AizeeException` with file path context.
4. [REQ] Frontmatter parsing: split on `---\n` boundaries. Validate required fields before use.
5. [REQ] `encoding="utf-8"` on all `read_text`/`write_text` for YAML files (Windows compat).
6. [PROHIBIT] `yaml.load(stream)` without explicit `Loader` (arbitrary code execution risk).
7. [PROHIBIT] Custom YAML tags from untrusted input.
[COMPAT]
- v6.0: current installed (6.0.3). Stable API.
[REFS]
- pyyaml.org/wiki/PyYAMLDocumentation
