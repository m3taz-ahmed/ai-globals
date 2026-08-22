[TECH] Ansible
[OBJ] Agentless configuration management and IT automation tool using YAML playbooks, Jinja2 templating, and SSH/WinRM for remote execution.
[RULES]
1. [REQ] Write idempotent tasks — every module invocation must produce the same result on repeated runs; use `creates`, `changed_when`, and `when` guards.
2. [REQ] Structure automation into Roles with standard layout (tasks/, handlers/, defaults/, vars/, templates/, files/, meta/); publish to Ansible Galaxy for reuse.
3. [REQ] Define inventory in INI or YAML format; use group_vars/ and host_vars/ directories for hierarchical variable management.
4. [REQ] Use `ansible-vault` to encrypt secrets (passwords, API keys, certs) at rest; store vault passwords in a file or integrate with a secrets manager (HashiCorp Vault, AWS Secrets Manager).
5. [REQ] Use dynamic inventory scripts or plugins (aws_ec2, gcp_compute, azure_rm) for cloud environments; refresh inventory before runs to capture scaling events.
6. [REQ] Pin Ansible collections and roles in `requirements.yml` with exact versions; run `ansible-galaxy collection install -r requirements.yml` before execution.
7. [REQ] Use `become: true` with explicit `become_user` for privilege escalation; avoid running entire playbooks as root.
8. [REQ] Test roles and playbooks with Molecule — define scenarios with driver (docker, podman, delegated), verifier (ansible, goss, testinfra), and idempotence checks.
9. [REQ] Use `check_mode: true` for dry-run validation in CI; ensure modules support check mode for safe previewing.
10. [CMD] Use `ansible-playbook -i inventory site.yml --tags <tag> --limit <host>` for targeted execution during iteration.
11. [CMD] Use `ansible-playbook --syntax-check` and `ansible-lint` in CI before merging playbooks to main.
12. [CMD] Use `ansible-vault encrypt/decrypt/view` for managing secrets; use `--vault-password-file` for non-interactive runs.
13. [PROHIBIT] Never store plaintext secrets in group_vars/host_vars — always vault-encrypt sensitive files.
14. [PROHIBIT] Never use `command` or `shell` modules when a native idempotent module exists (e.g., use `apt`/`yum` instead of `shell: apt-get install`).
15. [PROHIBIT] Never disable host key checking (`host_key_checking=False`) in production — it enables MITM attacks on SSH connections.
[COMPAT]
- ansible-core 2.16.x: Python 3.10+ required, improved module_utils, deprecation of old-style plugins
- ansible-core 2.17.x: Python 3.10+ required, performance improvements, new `ansible.builtin` module paths
- Ansible 9.x (community package): bundles ansible-core 2.16 + 100+ collections
[REFS]
- https://docs.ansible.com/ansible/latest/
- https://docs.ansible.com/ansible/latest/playbook_guide/
- https://molecule.readthedocs.io/
- https://galaxy.ansible.com/
