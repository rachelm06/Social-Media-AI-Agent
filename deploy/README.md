# Google Cloud VM Deployment Guide

This guide explains how to deploy the BiteRate Social Media AI Agent to a Google Cloud VM.

## Prerequisites

- Google Cloud SDK installed (`gcloud` CLI)
- Project created and APIs enabled
- Authentication configured (`gcloud auth login`)

## Project Setup

The project is configured as: **citric-lead-485119-j9**

### Required APIs

The following APIs have been enabled:
- ✅ Compute Engine API (`compute.googleapis.com`)
- ✅ OS Login API (`oslogin.googleapis.com`)
- ✅ Cloud Resource Manager API (`cloudresourcemanager.googleapis.com`)

## Deployment Steps

### 1. Create the VM

```bash
cd deploy
./create_vm.sh
```

This will:
- Create a VM instance named `biterate-agent-vm`
- Use `e2-micro` machine type (free tier eligible)
- Enable OS Login for secure SSH access
- Set up Ubuntu 22.04 LTS

### 2. Deploy the Application

```bash
./deploy_to_vm.sh
```

This will:
- Copy project files to the VM
- Run the setup script to install dependencies
- Set up the database schema
- Configure UV virtual environment

### 3. Configure Environment Variables

SSH into the VM:
```bash
gcloud compute ssh biterate-agent-vm --project=citric-lead-485119-j9 --zone=us-central1-a
```

Then create/edit `.env` file on the VM:
```bash
cd ~/bite-rate-agent
nano .env
```

Add all your API keys (Notion, OpenRouter, Replicate, Telegram, Mastodon).

### 4. Test the Agent

On the VM:
```bash
cd ~/bite-rate-agent
.venv/bin/python run.py
```

## Database Schema

The SQLite database schema is defined in `database/schema.sql` and includes:

- **reviews**: Stores reviews fetched from Notion
- **posts**: Stores generated social media posts
- **approvals**: Telegram approval history
- **feedback**: Rejection feedback for learning
- **replies**: Mastodon reply history
- **workflow_logs**: Execution logs

The database is automatically initialized when the application starts.

## Secure SSH Access

The VM uses OS Login for secure SSH access. You can connect using:

```bash
gcloud compute ssh biterate-agent-vm \
    --project=citric-lead-485119-j9 \
    --zone=us-central1-a
```

Or with IAP tunneling:
```bash
gcloud compute ssh biterate-agent-vm \
    --project=citric-lead-485119-j9 \
    --zone=us-central1-a \
    --tunnel-through-iap
```

## Running as a Service

The setup script creates a systemd service. To use it:

```bash
# Start the service
sudo systemctl start biterate-agent

# Enable on boot
sudo systemctl enable biterate-agent

# Check status
sudo systemctl status biterate-agent

# View logs
sudo journalctl -u biterate-agent -f
```

## VM Details

- **Name**: `biterate-agent-vm`
- **Zone**: `us-central1-a`
- **Machine Type**: `e2-micro` (1 vCPU, 1 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Disk**: 20 GB standard persistent disk

## Troubleshooting

### Check VM Status
```bash
gcloud compute instances describe biterate-agent-vm \
    --project=citric-lead-485119-j9 \
    --zone=us-central1-a
```

### View VM Logs
```bash
gcloud compute instances get-serial-port-output biterate-agent-vm \
    --project=citric-lead-485119-j9 \
    --zone=us-central1-a
```

### Restart VM
```bash
gcloud compute instances reset biterate-agent-vm \
    --project=citric-lead-485119-j9 \
    --zone=us-central1-a
```
