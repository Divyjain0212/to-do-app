#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

# ── 1. Install Ansible and Git ────────────────────────────────────────────────
apt-get update -y
apt-get install -y ansible python3 git

# ── 2. Write env file (values injected by Terraform templatefile) ─────────────
mkdir -p /etc/todo-app
cat > /etc/todo-app/app.env <<ENV
DB_HOST=${db_endpoint}
DB_PORT=3306
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
ENV
chmod 600 /etc/todo-app/app.env

# ── 3. Clone the repo to get the Ansible playbook ─────────────────────────────
git clone ${repo_url} /opt/todo-app

# ── 4. Run the Ansible playbook from the repo ─────────────────────────────────
ansible-playbook /opt/todo-app/ansible/playbooks/site.yml
