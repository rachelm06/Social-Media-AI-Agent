# FastAPI Usage Guide

The BiteRate Agent is now running as a FastAPI service on the VM.

## Service Status

The API is running as a systemd service and will automatically start on boot.

### Check Service Status
```bash
gcloud compute ssh biterate-agent-vm --project=citric-lead-485119-j9 --zone=us-central1-a
sudo systemctl status biterate-agent
```

### Start/Stop/Restart Service
```bash
sudo systemctl start biterate-agent
sudo systemctl stop biterate-agent
sudo systemctl restart biterate-agent
```

### View Logs
```bash
sudo journalctl -u biterate-agent -f
```

## API Endpoints

The API is available at: `http://localhost:8000` (on the VM)

### Interactive API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Available Endpoints

#### `GET /`
Root endpoint with API information

#### `GET /health`
Health check endpoint
```bash
curl http://localhost:8000/health
```

#### `POST /run`
Trigger the agent workflow
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

#### `GET /posts`
Get recent posts from database
```bash
curl http://localhost:8000/posts?limit=10
curl http://localhost:8000/posts?status=published
```

#### `GET /reviews`
Get reviews from database
```bash
curl http://localhost:8000/reviews?limit=10
```

#### `GET /stats`
Get workflow statistics
```bash
curl http://localhost:8000/stats
```

## Accessing from Outside the VM

To access the API from outside the VM, you'll need to:

1. **Add firewall rule** (if exposing externally):
```bash
gcloud compute firewall-rules create allow-biterate-api \
  --project=citric-lead-485119-j9 \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow FastAPI access"
```

2. **Or use SSH tunnel** (recommended for security):
```bash
gcloud compute ssh biterate-agent-vm \
  --project=citric-lead-485119-j9 \
  --zone=us-central1-a \
  -- -L 8000:localhost:8000
```

Then access at: `http://localhost:8000`

## Database

The SQLite database is located at: `~/bite-rate-agent/database/biterate.db`

You can query it directly:
```bash
sqlite3 ~/bite-rate-agent/database/biterate.db "SELECT * FROM posts LIMIT 5;"
```

## Testing the API

From your local machine (with SSH tunnel):
```bash
# Health check
curl http://localhost:8000/health

# Get stats
curl http://localhost:8000/stats

# Trigger agent workflow
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```
