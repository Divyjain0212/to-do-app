# Operational Runbook

## 1. Incident Response Flow
1. Acknowledge alert from SNS email.
2. Classify incident severity (SEV-1/2/3).
3. Check CloudWatch dashboard for scope (ALB, ASG, RDS).
4. Run targeted diagnostics.
5. Apply mitigation and confirm service recovery.
6. Record timeline and post-incident action items.

## 2. Debugging Workflows
### ALB Unhealthy Hosts
- Verify target health in ALB target group.
- Confirm app instance SG allows inbound port 8080 from ALB SG.
- Confirm `/health` endpoint returns 200 and timeout threshold is not too low.

### High EC2 CPU/Memory
- Inspect CloudWatch metrics and recent deployments.
- Verify autoscaling policy events and desired capacity.
- Check app logs for expensive queries or retry storms.

### RDS Latency / Connection Exhaustion
- Inspect `DatabaseConnections`, `CPUUtilization`, and free memory.
- Validate app pool settings (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).
- Evaluate instance class scaling or query optimization.

### IAM/Auth Failures
- Validate EC2 instance profile and attached policies.
- Confirm app runtime credentials and service permissions.

## 3. Rollback Procedures
1. Rolling deploy rollback:
- Cancel instance refresh.
- Restore prior launch template version.
2. Blue-green rollback:
- Shift ALB listener back to blue target group.
- Drain and investigate green environment.

## 4. Self-Healing Validation
- Terminate one app instance and verify ASG replacement.
- Confirm replacement instance registers healthy behind ALB.

## 5. Backup and Recovery
- Verify automated RDS snapshots daily.
- Monthly restore drill to a temporary instance and validate app-level reads.

## 6. Operational References
- Terraform: `terraform/`
- Ansible: `ansible/playbooks/site.yml`
- Jenkins Pipeline: `jenkins/Jenkinsfile`
- Dashboard Spec: `terraform/modules/monitoring/cloudwatch-dashboard.json`

## 7. Ansible Deployment (Manual IP Allocation)
1. After `terraform apply`, identify private IPs of running app instances in the ASG.
2. Add those private IPs under `[app]` in `ansible/inventory.ini` with `ansible_user=ubuntu`.
3. Set app runtime secrets/DB settings as environment variables before run:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SECRET_KEY`
4. Run deployment:
- `cd ansible`
- `ansible-playbook playbooks/site.yml`

Notes:
- Update `ansible/inventory.ini` whenever instance private IPs change.
