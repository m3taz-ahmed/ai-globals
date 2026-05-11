# Tech-Stack: AWS Infrastructure

> [!NOTE]
> **TRIGGER:** LOAD ON cloud architecture, infrastructure provisioning, Terraform module updates.
> **SCOPE:** AWS ECS, ALB, RDS Aurora, ElastiCache, S3, IAM. IaC: ref `tech-stack/terraform-iac.md`. DevOps: ref `rules/devops-standards.md`.

## 1. Compute & Networking
- Deploy applications to **ECS Fargate** to abstract underlying EC2 management.
- Configure distinct Task Definitions for Web (Octane), Queue Workers (Horizon), and Schedulers.
- Route traffic through an Application Load Balancer (ALB) configured with Target Groups, SSL termination (ACM), and strict Health Checks.
- Configure ECS Auto-scaling based on CPU/Memory utilization or request counts.

## 2. Databases & Storage
- Use **RDS Aurora Serverless v2** for PostgreSQL to handle variable workloads automatically via ACU scaling.
- Utilize RDS Proxy for connection pooling if not handled natively by PgBouncer.
- Deploy **ElastiCache Redis** in Cluster Mode across Multi-AZ for high availability.
- Store static assets and user uploads in **S3**, enforcing strict Bucket Policies (block public access, use CloudFront/Cloudflare distribution). Implement lifecycle rules for log/tmp buckets.

## 3. Messaging & Security
- Use **SQS** for decoupled microservices, ensuring Dead-Letter Queues (DLQ) are configured with appropriate visibility timeouts.
- Use **SES** for transactional emails, monitoring sending limits and using dedicated IPs for high volume.
- Store all sensitive credentials in **AWS Secrets Manager** and inject them at runtime via ECS task execution roles.
- Enforce IAM Least-Privilege patterns; tasks should only access what they explicitly need.
- Set up **CloudWatch Alarms** for high CPU, memory, 5xx errors, and DB connection limits.

## 4. Hard Constraints
- NEVER hardcode AWS credentials in code; rely on IAM Roles.
- NEVER expose RDS or ElastiCache clusters to the public internet; keep them in private subnets.
- ALWAYS encrypt data at rest (S3, RDS, EBS) using KMS.

---

## ✅ AWS INFRASTRUCTURE COMPLIANCE CHECK (Mandatory)
- [ ] **Security:** Are databases in private subnets and credentials managed by Secrets Manager?
- [ ] **Scalability:** Are ECS and Aurora configured for auto-scaling under load?
- [ ] **Observability:** Are CloudWatch alarms properly monitoring critical infrastructure thresholds?
