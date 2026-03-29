# Docker + Jenkins + Ansible Deployment Guide

## Overview
This setup enables a complete CI/CD pipeline using:
- **Dockerfile**: Builds Flask app as Docker image
- **Jenkins**: Orchestrates build, test, and deployment
- **Docker Hub**: Stores Docker images
- **Ansible**: Configures EC2 and runs Docker containers

## Components Created

### 1. Dockerfile (app/Dockerfile)
- Based on `python:3.12-slim`
- Installs dependencies from requirements.txt
- Runs Gunicorn on port 8080
- Includes health checks
- Non-root user for security

### 2. Jenkins Pipeline (jenkins/Jenkinsfile)
Stages:
1. **Checkout**: Clone repository
2. **Build Docker Image**: Build with tags (build-number + git-commit)
3. **Test Container**: Run pytest inside Docker container
4. **Login to Docker Hub**: Use Jenkins credentials (docker-hub-username, DOCKER_HUB_PASSWORD)
5. **Push to Docker Hub**: Push images with build tag and `latest` tag
6. **Rolling Deploy**: Terraform apply with new image URI

### 3. Ansible Playbook (ansible/playbooks/site.yml)
Tasks:
1. Install Docker
2. Create environment file at `/etc/todo-app/app.env`
3. Pull Docker image from Docker Hub
4. Install systemd service unit
5. Start todo-app container with:
   - Port 8080 mapping
   - Environment variables from app.env
   - Health checks
   - Auto-restart on failure

## Jenkins Credentials Required

Add these to Jenkins at **Manage Jenkins > Credentials**:

**Credential Type**: Username with password
- **ID**: `docker-hub-username`
- **Username**: Your Docker Hub username
- **Password**: Your Docker Hub access token

## Deployment Flow

```
Git Push
  ↓
Jenkins Trigger (webhook)
  ↓
Build Docker Image (tag: {build-number}-{commit-hash})
  ↓
Run Tests Inside Container
  ↓
Login to Docker Hub
  ↓
Push to Docker Hub (both specific tag and latest)
  ↓
Deploy: ansible-playbook with DOCKER_IMAGE_URI env var
  ↓
Ansible:
  - Installs Docker on EC2
  - Pulls image from Docker Hub
  - Creates systemd service
  - Starts container
  ↓
ALB Health Check Passes
  ↓
App Live!
```

## Manual Deployment Steps

### 1. Build Docker Image Locally
```bash
cd app
docker build -t your-dockerhub-username/todo-app:latest .
```

### 2. Push to Docker Hub
```bash
docker login
docker push your-dockerhub-username/todo-app:latest
```

### 3. Deploy with Ansible
Set environment variables in EC2 instances via Ansible:
```bash
export DOCKER_IMAGE_URI="your-dockerhub-username/todo-app:latest"
export DB_HOST="your-rds-endpoint"
export DB_USER="todoadmin"
export DB_PASSWORD="your-password"
export SECRET_KEY="your-secret"

ansible-playbook -i ansible/inventory.ini ansible/playbooks/site.yml
```

## Environment Variables (Passed to Container)
- `APP_PORT`: 8080
- `DB_HOST`: RDS endpoint
- `DB_NAME`: todo_dev
- `DB_USER`: todoadmin
- `DB_PASSWORD`: Database password
- `DB_PORT`: 3306
- `SECRET_KEY`: Flask secret key

## Monitoring & Troubleshooting

### SSH into Instance
```bash
ssh -i ansible/linux-key.pem ubuntu@{instance-ip}
```

### Check Service Status
```bash
sudo systemctl status todo-app
sudo journalctl -u todo-app -n 50 -f
```

### Check Docker Container
```bash
docker ps
docker logs todo-app
```

### Check ALB Health
```bash
aws elbv2 describe-target-health --target-group-arn {tg-arn}
```

## Next Steps
1. Configure Jenkins credentials for Docker Hub
2. Set up webhook from Git repository to Jenkins
3. Run Ansible playbook to deploy current image
4. Monitor container health and application logs
