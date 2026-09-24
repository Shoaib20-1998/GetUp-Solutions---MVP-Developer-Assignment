# Cloud Architecture

See `cloud-architecture.png` (source: `cloud-architecture.mmd`, a Mermaid diagram; rendered to PNG via `generate_architecture_diagram.py`). Target: AWS. No resources are provisioned; this is a design exercise only.

## Frontend hosting

The React SPA is built to static assets and served from an S3 bucket behind CloudFront. CloudFront terminates TLS at the edge, caches static assets globally, and is the only public entry point for the UI.

## API hosting

The FastAPI backend runs as a container on ECS Fargate, behind an Application Load Balancer. Fargate removes the need to manage EC2 instances; the service scales on request count or CPU. The ALB terminates TLS for API traffic and is the only public entry point for `/api`.

## Managed database

RDS for PostgreSQL, Multi-AZ, in the private data-tier subnet with no public IP. Only the ECS task security group can reach it on 5432. Automated daily backups plus point-in-time recovery cover the durability requirement without custom backup tooling.

## File storage for attachments

A dedicated S3 bucket, private by default, accessed only via the backend using short-lived credentials from its ECS task role (no bucket-level public access, no long-lived access keys). The backend proxies uploads and downloads rather than exposing pre-signed URLs directly to keep the same auth/visibility rules that apply to tickets applying to attachments too.

## Secrets management

AWS Secrets Manager holds the JWT signing key, the database credentials, and the AI provider API key (Gemini). The ECS task definition references secrets by ARN; they are injected as environment variables at container start and never baked into the image or committed to the repo (consistent with Requirement 12.1 in this same project).

## Networking and security basics

- HTTPS everywhere: CloudFront and the ALB both terminate TLS; nothing is served over plain HTTP.
- Private subnets: the app tier (ECS) and data tier (RDS) have no direct route to the internet. Only the ALB and CloudFront sit in public subnets.
- Access control: security groups are scoped tightly -- ALB accepts 443 from the internet, ECS accepts traffic only from the ALB's security group, RDS accepts traffic only from the ECS security group. IAM roles for the ECS task are scoped to exactly the S3 bucket and Secrets Manager entries it needs.

## Logging, monitoring, backups, scaling

- Logging: container stdout/stderr ships to CloudWatch Logs.
- Monitoring: CloudWatch alarms on ALB 5xx rate, ECS CPU/memory, and RDS storage/connections.
- Backups: RDS automated backups (point-in-time recovery) plus periodic manual snapshots before schema migrations.
- Scaling: ECS Fargate service auto-scales task count on CPU/request metrics; RDS scales vertically (instance class) since this MVP's write volume doesn't warrant read replicas or sharding.

## CI/CD

GitHub Actions triggers on push to `main`: run the backend test suite (Requirement 15) and the frontend typecheck/build, build the backend Docker image, push it to ECR, then update the ECS service to the new image (rolling deployment, zero downtime). The frontend build's static output syncs to the S3 bucket and CloudFront's cache is invalidated for the changed paths.
