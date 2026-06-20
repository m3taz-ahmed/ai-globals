[TECH] terraform-iac
[OBJ] Terraform IaC (AWS).
[RULES]
1. [REQ] Architecture: Reusable versioned modules. Explicit outputs. Data sources instead of hardcoded IDs.
2. [REQ] State: Remote storage. Native S3 Locking (TF 1.10+/OpenTofu). Native state encryption. Terragrunt for DRY envs.
3. [PROHIBIT] Constraints: NEVER commit `.tfstate`/secrets. NEVER manually create managed resources. ALWAYS `terraform fmt` and `tflint`.
4. [REQ] Workflow: `prevent_destroy = true` for data stores. Native testing (`terraform test`). CI/CD only.
