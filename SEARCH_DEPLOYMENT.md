# Midwinter Manual Search Deployment Guide

## Overview

The manual search feature consists of two components:
1. **Frontend**: `search.html` - Static HTML page with JavaScript
2. **Backend**: `search_api.py` - Flask API that calls Claude with MCP tools

## Prerequisites

- Python 3.10+
- Anthropic API key with MCP Midwinter tools configured
- Access to NAS for hosting

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file:

```
ANTHROPIC_API_KEY=your-api-key-here
```

### 3. Run the API Server

For development:

```bash
python search_api.py
```

For production (using gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 search_api:app
```

### 4. Update Frontend Configuration

Edit `search.html` and update the API endpoint:

```javascript
const API_BASE = 'http://your-nas-ip:5000/api';
```

Replace `your-nas-ip` with your actual NAS IP address or domain.

### 5. Deploy to NAS

1. Copy all HTML files to your NAS web directory
2. Run the Flask API server on the NAS (port 5000)
3. Ensure port 5000 is accessible from your network

## Running as a Service (Systemd)

Create `/etc/systemd/system/midwinter-search.service`:

```ini
[Unit]
Description=Midwinter Manual Search API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/midwinter-site
Environment="ANTHROPIC_API_KEY=your-key-here"
ExecStart=/usr/bin/python3 search_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable midwinter-search
sudo systemctl start midwinter-search
```

## Testing

1. Check API health:
   ```bash
   curl http://localhost:5000/api/health
   ```

2. Test search:
   ```bash
   curl -X POST http://localhost:5000/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "General Masters"}'
   ```

## Troubleshooting

- **API not responding**: Check if Flask server is running
- **CORS errors**: Ensure Flask-CORS is installed and configured
- **Search not working**: Verify Anthropic API key and MCP tools are configured
- **Slow responses**: Claude API calls can take 2-5 seconds per search

## Security Notes

- Keep your Anthropic API key secure
- Consider adding rate limiting for production use
- Run behind HTTPS in production
- Restrict API access to your local network if needed
