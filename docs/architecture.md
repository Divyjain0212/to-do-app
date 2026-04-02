# Architecture Notes

## Topology
- Internet traffic enters Application Load Balancer in public subnets.
- Flask application instances run in an Auto Scaling Group in private app subnets.
- RDS MySQL runs in private DB subnets with restricted access.

## Availability and Resilience
- Multi-AZ subnet design for ALB and app tier.
- ASG health checks and replacement for unhealthy instances.
- CloudWatch alarms with SNS notifications for proactive incident response.

## Security
- Security groups enforce tier-to-tier access only.
- RDS is not publicly accessible.
- EC2 uses IAM role for systems management and observability integrations.

## Automation
- Terraform provisions core infrastructure and EC2 instances.
- User-data script (in EC2 launch) automates:
  - Package installation (Ansible, AWS CLI, Docker)
  - S3 config retrieval (`.env`, `nginx.conf`, Ansible playbook)
  - Ansible playbook execution for host-level convergence
  - Systemd service creation and startup
- Jenkins orchestrates validation, updates, and deployment strategy.
- Docker container self-heals via systemd restart policy and health checks.