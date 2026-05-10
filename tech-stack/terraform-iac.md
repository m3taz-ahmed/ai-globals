# Tech-Stack: Terraform IaC

> [!NOTE]
> **TRIGGER:** LOAD ON infrastructure provisioning, cloud resource configuration.
> **SCOPE:** Terraform, Terragrunt, AWS.

## 1. Module Architecture & HCL Patterns
- Structure code into reusable, versioned modules (e.g., `vpc`, `ecs-cluster`, `rds-aurora`).
- Use variables and locals effectively to ensure modules are highly configurable without hardcoding environment specifics.
- Define explicit output values to pass IDs and ARNs between modules.
- Utilize data sources to reference existing infrastructure rather than hardcoding IDs.

## 2. State & Environment Management
- ALWAYS use remote state storage. Configure an S3 backend with DynamoDB locking for concurrency control.
- Use Terragrunt to keep multi-environment configurations DRY (Don't Repeat Yourself) by inheriting common settings.
- Avoid using Terraform Workspaces for separate environments; use separate directory structures or Terragrunt instead.

## 3. Workflow & Lifecycle
- Define lifecycle rules (e.g., `prevent_destroy = true`) for stateful resources like RDS databases and S3 buckets containing user data.
- Use the `terraform import` command to bring existing unmanaged resources under IaC control.
- Enforce the `plan -> apply` workflow via CI/CD, never from local machines for production environments.

## 4. Hard Constraints
- NEVER commit `.tfstate` files or sensitive variables (e.g., `terraform.tfvars` with secrets) to source control.
- NEVER manually create resources in the AWS Console if they belong to the Terraform scope.
- ALWAYS run `terraform fmt` and `tflint` before opening a pull request.

---

## ✅ TERRAFORM IAC COMPLIANCE CHECK (Mandatory)
- [ ] **State Management:** Is the remote state backend configured with DynamoDB locking?
- [ ] **Drift Prevention:** Are all infrastructure changes made exclusively via Terraform?
- [ ] **Safety:** Are `prevent_destroy` lifecycle rules applied to critical data stores?
