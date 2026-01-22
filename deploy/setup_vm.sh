#!/bin/bash
# Setup script for Google Cloud VM
# This script will be run on the VM to set up the environment

set -e

echo "🚀 Setting up BiteRate Social Media AI Agent on VM..."

# Update system
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl sqlite3

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Get the actual user (not root if run with sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
if [ "$ACTUAL_USER" = "root" ]; then
    ACTUAL_USER=$(who am i | awk '{print $1}')
fi

# Navigate to user's home directory
if [ -n "$ACTUAL_USER" ] && [ "$ACTUAL_USER" != "root" ]; then
    cd /home/$ACTUAL_USER/bite-rate-agent 2>/dev/null || cd ~/bite-rate-agent
else
    cd ~/bite-rate-agent
fi

# Initialize database
if [ ! -f "database/biterate.db" ]; then
    mkdir -p database
    sqlite3 database/biterate.db < database/schema.sql
    echo "✓ Database initialized"
fi

# Set up UV environment
if [ ! -d ".venv" ]; then
    uv venv
    echo "✓ Virtual environment created"
fi

# Install dependencies
uv sync
echo "✓ Dependencies installed"

# Set up systemd service for FastAPI (optional, for running as a service)
sudo tee /etc/systemd/system/biterate-agent.service > /dev/null <<EOF
[Unit]
Description=BiteRate Social Media AI Agent API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$(pwd)"
ExecStart=$(pwd)/.venv/bin/uvicorn src.api:app --host 0.0.0.0 --port 8000 --working-dir $(pwd)
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Systemd service configured for FastAPI"
echo "🎉 Setup complete!"
echo ""
echo "To start the API service: sudo systemctl start biterate-agent"
echo "To enable on boot: sudo systemctl enable biterate-agent"
echo "To check status: sudo systemctl status biterate-agent"
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
