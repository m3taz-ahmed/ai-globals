---
name: api-versioning
description: API versioning strategies and lifecycle management for backward-compatible evolution
---
[SKILL] api-versioning
[OBJ] Design and maintain APIs with clear versioning strategies that preserve backward compatibility and provide predictable deprecation paths.
[RULES]
1. [REQ] Support at least one explicit versioning strategy: URI versioning (e.g. /v1/), header versioning (e.g. Accept-Version), query parameter (e.g. ?api-version=), or content negotiation (Accept header media types).
2. [REQ] Use semantic versioning (semver) for all API releases; bump the major version for any breaking change, minor for additive, patch for fixes.
3. [REQ] Maintain backward compatibility within a major version; never introduce a breaking change without a new major version.
4. [REQ] Provide a deprecation window of minimum 6 months between announcing deprecation and removing functionality.
5. [REQ] Emit Sunset and Deprecation HTTP headers on deprecated endpoints with the scheduled removal date.
6. [REQ] Publish versioned documentation so each major version has its own complete reference; do not overwrite prior version docs.
7. [REQ] Maintain a per-version changelog documenting additions, deprecations, fixes, and breaking changes for every release.
8. [CMD] Announce deprecations through release notes, response headers, and developer communication channels simultaneously.
9. [CMD] Run old and new versions in parallel during the deprecation window so clients can migrate incrementally.
10. [CMD] Track per-version usage metrics to confirm adoption of the new version before retiring the old one.
11. [PROHIBIT] Shipping unversioned breaking changes that silently alter existing client contracts.
12. [PROHIBIT] Removing fields, parameters, or endpoints without first marking them deprecated and serving a deprecation window.
