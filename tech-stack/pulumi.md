[TECH] Pulumi
[OBJ] Infrastructure-as-code engine that provisions cloud resources using real programming languages (TypeScript, Python, Go, C#, Java) with state management.
[RULES]
1. [REQ] Define infrastructure as Programs (entry point) that create resources; compose reusable infrastructure as Components (pulumi.ComponentResource) with explicit inputs and outputs.
2. [REQ] Use Stacks (e.g., `dev`, `staging`, `prod`) with stack-specific configuration via `pulumi config set --stack <name>`; store config in `Pulumi.<stack>.yaml`.
3. [REQ] Manage state via Pulumi Service backend or self-hosted S3/Azure Blob/GCS backend; run `pulumi stack export` periodically for offline backups.
4. [REQ] Use `pulumi config set-secret` for sensitive values; secrets are encrypted at rest with the stack's encryption key (KMS, Azure Key Vault, or passphrase).
5. [REQ] Use ESC (Environments, Secrets, and Configuration) to share configuration across stacks and projects; reference ESC environments in stack config.
6. [REQ] Define CrossGuard (Policy as Code) packs with `pulumi-policy` to enforce resource constraints (e.g., no public S3 buckets, required tags, allowed regions).
7. [REQ] Use resource aliases (`aliases: [...]`) when renaming or restructuring resources to prevent destructive replacement during refactors.
8. [REQ] Use `pulumi preview` in CI before `pulumi up`; fail the pipeline on any unexpected deletions or replacements.
9. [REQ] Tag all resources with consistent metadata (project, environment, owner, cost-center) using `pulumi:tags` or provider-specific tag properties.
10. [CMD] Use `pulumi import <type> <name> <id>` to bring existing cloud resources under Pulumi management; generate code with `--generate-code`.
11. [CMD] Use `pulumi destroy --skip-preview` only for ephemeral stacks; always preview for production teardowns.
12. [CMD] Use `pulumi stack select <org>/<project>/<stack>` to switch contexts; use `pulumi stack ls` to audit active stacks.
13. [PROHIBIT] Never store secrets in plaintext in `Pulumi.<stack>.yaml` — always use `set-secret` or ESC references.
14. [PROHIBIT] Never run `pulumi up` without `--preview` or `pulumi preview` in CI for production stacks.
15. [PROHIBIT] Never delete the state backend (S3 bucket / Pulumi Service project) without first exporting state — orphaned resources cannot be managed afterward.
[COMPAT]
- v3.110.x: ESC GA, improved `pulumi import`, native Go SDK improvements
- v3.115.x: Component resources with provider propagation, `pulumi watch` for dev loops
- v3.120.x: Policy Pack v2 schema, YAML provider improvements
[REFS]
- https://www.pulumi.com/docs/
- https://www.pulumi.com/docs/concepts/programs/
- https://www.pulumi.com/docs/esc/
- https://www.pulumi.com/docs/crossguard/
