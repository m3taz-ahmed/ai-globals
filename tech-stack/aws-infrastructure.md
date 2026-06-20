[TECH] aws-infrastructure
[OBJ] AWS Infrastructure Deployment.
[RULES]
1. [REQ] Compute: ECS Fargate. Graviton4 (ARM64) FIRST. ALB with ACM and Health Checks.
2. [REQ] Database: RDS Aurora Serverless v2 (PostgreSQL). ElastiCache Redis Cluster (Multi-AZ).
3. [REQ] Messaging: SQS with DLQ. SES for emails.
4. [PROHIBIT] Security: NEVER hardcode credentials (use Secrets Manager/IAM Roles). NEVER expose RDS/Redis publicly.
5. [REQ] Encryption: KMS encryption at rest (S3, RDS, EBS).
