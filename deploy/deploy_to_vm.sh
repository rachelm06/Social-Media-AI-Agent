#!/bin/bash
# Script to deploy the project to the VM
# This copies files and sets up the environment

set -e

PROJECT_ID="citric-lead-485119-j9"
ZONE="us-central1-a"
VM_NAME="biterate-agent-vm"

echo "📦 Deploying BiteRate Agent to VM..."

# Get VM IP
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Connecting to VM at $EXTERNAL_IP..."

# Create remote directory
gcloud compute ssh $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --command="mkdir -p ~/bite-rate-agent"

# Copy project files (excluding .venv, __pycache__, etc.)
echo "Copying project files..."
# Get the project root directory (parent of deploy/)
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Create a temporary tar archive excluding unwanted files
cd "$PROJECT_ROOT"
tar --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='database/*.db' \
    --exclude='*.db-journal' \
    --exclude='.Trash' \
    -czf /tmp/biterate-deploy.tar.gz \
    .

# Copy the archive to VM
gcloud compute scp \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    /tmp/biterate-deploy.tar.gz \
    $VM_NAME:/tmp/

# Extract on VM
gcloud compute ssh $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --command="mkdir -p ~/bite-rate-agent && cd ~/bite-rate-agent && tar -xzf /tmp/biterate-deploy.tar.gz && rm /tmp/biterate-deploy.tar.gz"

# Copy setup script
gcloud compute scp \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    deploy/setup_vm.sh \
    $VM_NAME:~/bite-rate-agent/

# Make setup script executable and run it
echo "Running setup script on VM..."
gcloud compute ssh $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --command="cd ~/bite-rate-agent && chmod +x deploy/setup_vm.sh && bash deploy/setup_vm.sh"

echo "✓ Deployment complete!"
echo ""
echo "To SSH into the VM:"
echo "  gcloud compute ssh $VM_NAME --project=$PROJECT_ID --zone=$ZONE"
echo ""
echo "Don't forget to:"
echo "1. Copy your .env file to the VM with API keys"
echo "2. Test the agent: cd ~/bite-rate-agent && .venv/bin/python run.py"
