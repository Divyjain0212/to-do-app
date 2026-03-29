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
- Terraform provisions core infrastructure.
- Ansible converges host-level configuration.
- Jenkins orchestrates validation and deployment strategy.
