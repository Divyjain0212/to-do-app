#!/bin/bash
set -e

# Update package lists
apt-get update
apt-get install -y ca-certificates curl python3-docker awscli ansible

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: \$(. /etc/os-release && echo "\${UBUNTU_CODENAME:-\$VERSION_CODENAME}")
Components: stable
Architectures: \$(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Create directories
mkdir -p /etc/todo-app

# Try to download .env from S3, if it fails create from Terraform variables
ENV_FILE="/etc/todo-app/app.env"
if ! aws s3 cp "s3://${assets_bucket_name}/${config_s3_prefix}/.env" "$ENV_FILE"; then
  echo "Creating .env from Terraform variables"
  cat > "$ENV_FILE" <<EOF
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_username}
DB_PASSWORD=${db_password}
DB_PORT=3306
APP_PORT=8000
SECRET_KEY=${app_secret_key}
GOOGLE_CLIENT_ID=${google_client_id}
GOOGLE_CLIENT_SECRET=${google_client_secret}
GOOGLE_REDIRECT_URI=${google_redirect_uri}
EOF
fi

chmod 600 "$ENV_FILE"

# Download Ansible playbook from S3
mkdir -p /opt/myapp
PLAYBOOK_FILE="/opt/myapp/site.yml"
aws s3 cp "s3://${assets_bucket_name}/${config_s3_prefix}/site.yml" "$PLAYBOOK_FILE" || true

# Run Ansible playbook
if [ -f "$PLAYBOOK_FILE" ]; then
  ansible-playbook -i "localhost," -c local "$PLAYBOOK_FILE" -e "target_hosts=localhost"
fi
