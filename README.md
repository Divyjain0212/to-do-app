# AWS 3-Tier Todo App Capstone

This repository contains a production-style capstone project for troubleshooting, automation, and high availability on AWS.

## Scope
- 3-tier architecture with ALB, Auto Scaling EC2 app tier, and private RDS MySQL.
- Infrastructure as Code with Terraform.
- CI/CD with Jenkins (running in local Docker).
- Configuration management and patching with Ansible.
- Monitoring and alerting with CloudWatch and SNS.
- Operational runbook and RCA evidence pack.
- Multi-user authentication with sign up, sign in, and optional Google OAuth.

## Repository Layout
- `app/`: Flask todo application and tests.
- `terraform/`: AWS infrastructure modules and root wiring.
- `ansible/`: Playbooks and roles for host and app configuration.
- `jenkins/`: CI/CD pipeline definition.
- `terraform/modules/monitoring/`: Dashboard and alarm definitions.
- `docs/`: Runbook, architecture notes, and RCA template.

## Quick Start (Local App)
1. Create a Python virtual environment.
2. Install dependencies from `app/requirements.txt`.
3. Optionally create `app/.env` for local environment variables.
4. Run locally with no DB env vars to use SQLite default (`todo.db`).
5. For MySQL, set environment variables:
   - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
6. Set `SECRET_KEY` in `app/.env` for secure session cookies.
7. Optional Google OAuth setup in `app/.env`:
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI` (for local: `http://127.0.0.1:8081/auth/google/callback`)
   - In Google Cloud Console, add authorized redirect URI that matches `GOOGLE_REDIRECT_URI` exactly
8. For production cookie hardening set in `app/.env`:
   - `SESSION_COOKIE_SECURE=true` (HTTPS only)
   - `SESSION_COOKIE_SAMESITE=Lax` or `Strict`
   - `SESSION_TTL_HOURS=12` (or your policy)
9. Run `python app/src/app.py`.
10. Open frontend UI at `http://127.0.0.1:8081/`.
11. Check health endpoint at `http://127.0.0.1:8081/health`.

Default app port is `8081` to avoid conflict with Jenkins on `8080`.
API discovery endpoint is available at `http://127.0.0.1:8081/api`.

At startup the app logs which DB backend is active (for example, `sqlite` or `mysql`).

## AWS Deployment Flow
1. Initialize and apply Terraform in `terraform/`.
2. Configure application hosts with Ansible playbooks.
3. Run Jenkins pipeline from `jenkins/Jenkinsfile` for deployment strategy.
4. Validate dashboards, alarms, and self-healing behavior.

### Terraform Environments
- Development vars: `terraform/environments/development.tfvars`
- Production vars: `terraform/environments/production.tfvars`

Run development:
1. `cd terraform`
2. `terraform init`
3. `terraform plan -var-file=environments/development.tfvars`
4. `terraform apply -var-file=environments/development.tfvars`

Run production:
1. `cd terraform`
2. `terraform init`
3. `terraform plan -var-file=environments/production.tfvars`
4. `terraform apply -var-file=environments/production.tfvars`

Before apply:
- Replace `app_ami_id` placeholders in both tfvars files.
- Replace `db_password` placeholders with strong secrets.

## Notes
- Defaults are conservative and intended for a capstone demonstration.
- Fill placeholders in docs with measured metrics after test runs.
- MySQL 8 default auth plugins can require `cryptography` when using PyMySQL.
