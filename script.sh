#!/bin/bash
""" Ensure that your system is up to date and that you have installed 
the gnupg and software-properties-common packages. 
You will use these packages to verify HashiCorp's 
GPG signature and install HashiCorp's Debian package repository"""

sudo apt-get update && sudo apt-get install -y gnupg software-properties-common

# Install HashiCorp's GPG key.

wget -O- https://apt.releases.hashicorp.com/gpg | \
gpg --dearmor | \
sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null

# Verify the GPG key's fingerprint.

gpg --no-default-keyring \
--keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
--fingerprint

# The gpg command reports the key fingerprint:

"""/usr/share/keyrings/hashicorp-archive-keyring.gpg
-------------------------------------------------
pub   rsa4096 XXXX-XX-XX [SC]
AAAA AAAA AAAA AAAA
uid         [ unknown] HashiCorp Security (HashiCorp Package Signing) <security+packaging@hashicorp.com>
sub   rsa4096 XXXX-XX-XX [E]"""

# Add the official HashiCorp repository to your system.

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

# Update apt to download the package information from the HashiCorp repository.

sudo apt update

#Install Terraform from the new repository.

sudo apt-get install terraform -y

# Install Ansible on Ubuntu
sudo apt install software-properties-common  -y
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible -y

# Install Java on Ubuntu
sudo apt update
sudo apt install fontconfig openjdk-21-jre -y
java -version

# Install Jenkins on Ubuntu
sudo wget -O /etc/apt/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key
echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc]" \
  https://pkg.jenkins.io/debian-stable binary/ | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt update
sudo apt install jenkins -y

# Install Docker on  Ubuntu
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update

sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
sudo usermod -aG docker $USER && newgrp docker

# Add jenkins user to docker group so Jenkins can run docker commands
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

# Install Python, pip and pytest for running tests in Jenkins
sudo apt install -y python3 python3-pip 

# Install app dependencies globally so Jenkins can run pytest
sudo pip3 install --break-system-packages \
  pytest \
  pytest-cov \
  flask \
  pymysql \
  python-dotenv \
  python-json-logger \
  cryptography \
  werkzeug

echo "✅ Jenkins server setup complete"
echo "Access Jenkins at: http://$(curl -s ifconfig.me):8080"
echo "Initial admin password: $(sudo cat /var/lib/jenkins/secrets/initialAdminPassword)"