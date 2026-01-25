# Midwinter Website Infrastructure Documentation

## Overview

The Midwinter website is hosted on a QNAP NAS (10.0.0.55) and served via Cloudflare Tunnel. This document describes the complete architecture and how services initialize on reboot.

## Architecture Diagram

```
Internet
    │
    ▼
Cloudflare Tunnel (ad262502-019f-4356-aa6f-0bbe8a738144)
    │
    ├── midwinter-remaster.titanium-helix.com → localhost:80 (QNAP Web Server)
    │                                               │
    │                                               └── /share/Web/ (static files)
    │                                                   ├── *.html (pages)
    │                                                   ├── api-proxy/ (PHP proxies)
    │                                                   ├── forms/ (mailing list)
    │                                                   └── releases/ → /share/midwinter/releases/
    │
    └── api.midwinter-remaster.titanium-helix.com → localhost:8500 (Flask API)
                                                        │
                                                        └── Docker: midwinter-search-api
                                                            └── search_api.py (Claude MCP)
```

## Services & Initialization

### 1. Cloudflare Tunnel (cloudflared)

**Location:** `/share/CACHEDEV1_DATA/homes/fischb/`

**Files:**
- `cloudflared-linux-amd64` - Binary
- `.cloudflared/config.yml` - Tunnel configuration
- `.cloudflared/ad262502-019f-4356-aa6f-0bbe8a738144.json` - Credentials
- `start-cloudflared.sh` - Manual start script
- `cloudflared.log` - Logs

**Configuration (`config.yml`):**
```yaml
tunnel: ad262502-019f-4356-aa6f-0bbe8a738144
credentials-file: /share/CACHEDEV1_DATA/homes/fischb/.cloudflared/ad262502-019f-4356-aa6f-0bbe8a738144.json

ingress:
  - hostname: midwinter-remaster.titanium-helix.com
    service: http://localhost:80
  - hostname: api.midwinter-remaster.titanium-helix.com
    service: http://localhost:8500
  - service: http_status:404
```

**Auto-Start on Reboot:**
```
/share/CACHEDEV1_DATA/.qpkg/autorun/autorun.sh
```
```bash
#!/bin/sh
# Auto-start cloudflared tunnel after NAS boot
sleep 30
cd /share/CACHEDEV1_DATA/homes/fischb
./cloudflared-linux-amd64 tunnel --config .cloudflared/config.yml run >> cloudflared.log 2>&1 &
echo "Cloudflared auto-started at $(date)" >> cloudflared.log
```

**Manual Start:**
```bash
ssh fischb@10.0.0.55 "/share/homes/fischb/start-cloudflared.sh"
```

**Check Status:**
```bash
ssh fischb@10.0.0.55 "ps aux | grep cloudflared"
ssh fischb@10.0.0.55 "tail -20 /share/homes/fischb/cloudflared.log"
```

---

### 2. Container Station (Docker)

**Location:** `/share/CACHEDEV1_DATA/.qpkg/container-station/`

**Key Script:** `script/start-stop.sh` - Handles all container lifecycle

**Auto-Start:** Container Station is a QPKG that auto-starts on boot via QNAP's init system. It's enabled in `/etc/config/qpkg.conf`:
```ini
[container-station]
Enable = TRUE
RC_Number = 101
```

**Docker Socket:** `unix:///var/run/system-docker.sock`

**Docker CLI Path:** `/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker`

**List Containers:**
```bash
ssh fischb@10.0.0.55 "export DOCKER_HOST=unix:///var/run/system-docker.sock; /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker ps -a"
```

---

### 3. Flask Search API (MCP/Claude Integration)

**Location:** `/share/Web/api/`

**Files:**
- `search_api.py` - Main Flask application
- `midwinter_unified.db` - SQLite database with manual content
- `start_api.sh` - Docker startup script
- `Dockerfile` - Container build file
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API key)

**Port:** 8500 (internal), proxied via Cloudflare to `api.midwinter-remaster.titanium-helix.com`

**Features:**
- `/api/health` - Health check endpoint
- `/api/search` - Natural language search using Claude with MCP tools
- `/api/search/section` - Section-filtered search
- `/api/mailing-list` - Mailing list signup (also in Flask)

**Claude Integration:**
- Uses Anthropic API with claude-sonnet-4-5-20250929 model
- Implements MCP-style tools: `search_manual`, `quick_search`
- Searches SQLite database with FTS (Full Text Search)

**Start the Container:**
```bash
ssh fischb@10.0.0.55 "bash /share/Web/api/start_api.sh"
```

**start_api.sh contents:**
```bash
#!/bin/sh
export DOCKER_HOST=unix:///var/run/system-docker.sock
DOCKER=/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker

$DOCKER stop midwinter-search-api 2>/dev/null
$DOCKER rm midwinter-search-api 2>/dev/null

$DOCKER run -d \
  --name midwinter-search-api \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /share/Web/api:/app \
  -w /app \
  -e ANTHROPIC_API_KEY="<key>" \
  python:3.11-slim \
  sh -c "pip install --no-cache-dir -r requirements.txt && python search_api.py"
```

**IMPORTANT:** The container uses `--restart unless-stopped` which means it auto-restarts on NAS reboot once Container Station is running.

**Test the API:**
```bash
curl http://10.0.0.55:8500/api/health
curl -X POST http://10.0.0.55:8500/api/search -H "Content-Type: application/json" -d '{"query": "General Masters"}'
```

---

### 4. PHP API Proxy

**Location:** `/share/Web/api-proxy/`

The search page uses PHP proxies to forward requests to the Flask API. This avoids CORS issues and keeps the API internal.

**Files:**
- `search.php` - Proxies to `/api/search`
- `search/section.php` - Proxies to `/api/search/section`

**How it works:**
```php
// search.php
$ch = curl_init('http://localhost:8500/api/search');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
// ... forward to Flask and return response
```

---

### 5. Mailing List Form

**Location:** `/share/Web/forms/`

**Files:**
- `mailing-list.php` - Form handler
- `mailing_list.csv` - Submission log
- `SETUP_INSTRUCTIONS.txt` - Setup guide
- `.rate_*` - Rate limit files

**How it works:**
1. Form on `recruit.html` submits to `forms/mailing-list.php`
2. PHP connects to Gmail SMTP (ssl://smtp.gmail.com:465)
3. Sends email to lane01evan@gmail.com
4. Logs submission to CSV
5. Implements rate limiting (1 per minute per IP)

**Gmail Credentials:**
- User: `lane01evan@gmail.com`
- App Password: `onkojkqiecgkktbo` (Gmail App Password, not regular password)

**Test the form:**
```bash
curl -X POST http://10.0.0.55/forms/mailing-list.php \
  -d "name=Test" -d "email=test@example.com" -d "role=fan" -d "message=Test"
```

---

### 6. Download Links / Releases

**Location:** `/share/midwinter/releases/`

**Symlink in Web:** `/share/Web/releases` → `/share/midwinter/releases`

**Current Releases:**
- v0.5.8
- v0.5.9
- v0.6.0
- v0.6.0-preview

**Download URLs (in download.html):**
```
https://midwinter-remaster.titanium-helix.com/releases/v0.6.0/MW-windows-v0.6.0.zip
https://midwinter-remaster.titanium-helix.com/releases/v0.6.0/MW-mac-apple-silicon-v0.6.0.zip
https://midwinter-remaster.titanium-helix.com/releases/v0.6.0/MW-mac-intel-v0.6.0.zip
https://midwinter-remaster.titanium-helix.com/releases/v0.6.0/MW-linux-v0.6.0.zip
```

---

## Full Reboot Sequence

When the NAS reboots, services start in this order:

1. **QNAP OS boots**
2. **Container Station QPKG starts** (RC_Number 101)
   - Creates Docker networks/bridges
   - Starts system-docker daemon
   - Containers with `--restart unless-stopped` auto-start
3. **autorun.sh executes** (after 30s delay)
   - Starts cloudflared tunnel
4. **Web Server (httpd) starts**
   - Serves `/share/Web/` on port 80
5. **Flask API container starts** (via Docker restart policy)
   - Listens on port 8500

---

## Troubleshooting

### Cloudflare Tunnel Not Working
```bash
# Check if running
ssh fischb@10.0.0.55 "ps aux | grep cloudflared"

# Check logs
ssh fischb@10.0.0.55 "tail -50 /share/homes/fischb/cloudflared.log"

# Restart manually
ssh fischb@10.0.0.55 "pkill cloudflared; /share/homes/fischb/start-cloudflared.sh"
```

### Flask API Not Responding
```bash
# Check container status
ssh fischb@10.0.0.55 "export DOCKER_HOST=unix:///var/run/system-docker.sock; /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker ps -a"

# View container logs
ssh fischb@10.0.0.55 "export DOCKER_HOST=unix:///var/run/system-docker.sock; /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker logs midwinter-search-api"

# Restart container
ssh fischb@10.0.0.55 "bash /share/Web/api/start_api.sh"
```

### Email Form Not Working
```bash
# Test PHP directly
ssh fischb@10.0.0.55 "php /share/Web/forms/mailing-list.php"

# Check rate limit files
ssh fischb@10.0.0.55 "ls -la /share/Web/forms/.rate_*"

# View submission log
ssh fischb@10.0.0.55 "cat /share/Web/forms/mailing_list.csv"
```

### Search Not Working
```bash
# Test health endpoint
curl https://midwinter-remaster.titanium-helix.com/api-proxy/health.php

# Test internal API
ssh fischb@10.0.0.55 "curl http://localhost:8500/api/health"

# Check if Anthropic API key is set
ssh fischb@10.0.0.55 "cat /share/Web/api/.env"
```

---

## Key Files Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| Website Root | `/share/Web/` | All HTML, CSS, images |
| Cloudflared | `/share/homes/fischb/cloudflared-linux-amd64` | Tunnel binary |
| Tunnel Config | `/share/homes/fischb/.cloudflared/config.yml` | Routing rules |
| Autorun | `/share/CACHEDEV1_DATA/.qpkg/autorun/autorun.sh` | Boot startup |
| Flask API | `/share/Web/api/search_api.py` | Search backend |
| Database | `/share/Web/api/midwinter_unified.db` | Manual content |
| Mailing Form | `/share/Web/forms/mailing-list.php` | Email handler |
| Releases | `/share/midwinter/releases/` | Download files |
| Container Station | `/share/CACHEDEV1_DATA/.qpkg/container-station/` | Docker management |

---

## NAS Access

**SSH:** `ssh fischb@10.0.0.55`
**Credentials:** fischb / Arch3rD0g6074

---

## Domain

**Primary:** midwinter-remaster.titanium-helix.com
**API:** api.midwinter-remaster.titanium-helix.com (currently unused, API proxied via PHP)
