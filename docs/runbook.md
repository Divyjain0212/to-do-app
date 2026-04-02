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

### Systemd Service Failed to Start
- Check systemd journal: `journalctl -u todo-app -n 50`
- Verify `/etc/todo-app/app.env` exists and has correct permissions (600).
- Confirm Docker image URI is accessible and correctly tagged.
- Validate S3 bucket and configuration files were downloaded successfully.

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
- Instance Initialization: `terraform/modules/compute/user-data.sh`
- Ansible Playbook: `ansible/playbooks/site.yml`
- Jenkins Pipeline: `jenkins/Jenkinsfile`
- Dashboard Spec: `terraform/modules/monitoring/cloudwatch-dashboard.json`
- Systemd Service: `/etc/systemd/system/todo-app.service` (auto-created at boot)

## 7. Application Deployment (Automated via User-Data)
Deployment is fully automated through the EC2 user-data script:
1. Script downloads config files (`.env`, `nginx.conf`, Ansible playbook) from S3.
2. Generates fallback `.env` from Terraform variables if S3 retrieval fails.
3. Runs Ansible playbook to converge system state.
4. Creates and starts `todo-app` systemd service.
5. Docker container auto-restarts on failure (with health checks).

**Manual Troubleshooting:**
- SSH to instance and check: `sudo systemctl status todo-app`
- View logs: `sudo journalctl -u todo-app -f`
- Re-run playbook: `cd /opt/myapp && ansible-playbook -i "localhost," -c local site.yml`
- Manually restart service: `sudo systemctl restart todo-app`

Notes:
- Ensure S3 bucket and Terraform variables are correctly configured.
- User-data script runs only once at instance launch; changes require new instance or manual playbook execution.
