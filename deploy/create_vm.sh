#!/bin/bash
# Script to create and deploy VM on Google Cloud
# This uses OS Login for secure SSH access

set -e

PROJECT_ID="citric-lead-485119-j9"
ZONE="us-central1-a"
VM_NAME="biterate-agent-vm"
MACHINE_TYPE="e2-micro"  # Free tier eligible
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "🔧 Creating VM: $VM_NAME in project $PROJECT_ID..."

# Create VM with OS Login enabled
gcloud compute instances create $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --image-family=$IMAGE_FAMILY \
    --image-project=$IMAGE_PROJECT \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --metadata=enable-oslogin=TRUE \
    --tags=http-server,https-server \
    --scopes=https://www.googleapis.com/auth/cloud-platform

echo "✓ VM created successfully!"
echo ""
echo "Waiting for VM to be ready..."
sleep 10

# Get the VM's external IP
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "🌐 VM External IP: $EXTERNAL_IP"
echo ""
echo "To SSH into the VM:"
echo "  gcloud compute ssh $VM_NAME --project=$PROJECT_ID --zone=$ZONE"
echo ""
echo "Or using OS Login:"
echo "  gcloud compute ssh $VM_NAME --project=$PROJECT_ID --zone=$ZONE --tunnel-through-iap"
echo ""
echo "Next steps:"
echo "1. Copy project files to VM"
echo "2. Run setup_vm.sh on the VM"
echo "3. Configure .env file with API keys"
