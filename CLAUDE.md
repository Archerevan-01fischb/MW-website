# Claude Code Development Guidance for MW Website

**Agent**: Claude Code
**Project Type**: Static Website + Flask API
**Domain**: midwinter-remaster.titanium-helix.com

---

## Development Workflow

### 1. Local Preview (before deploying)
Start a local server to preview changes:

**Option A - VS Code Live Server:**
- Install "Live Server" extension by Ritwick Dey
- Right-click any HTML file → "Open with Live Server"
- Browser auto-refreshes on save

**Option B - Command Line:**
```bash
# From project directory
npx live-server
# Or without auto-refresh:
python -m http.server 8080
```

Then open http://localhost:8080 (or the port shown)

### 2. Deploy to Staging (test first)
```powershell
.\deploy-staging.ps1
```
- Staging URL: https://staging.midwinter-remaster.titanium-helix.com
- Internal: http://10.0.0.55:8082
- Full PHP replica with working email and search

### 3. Deploy to Production
**IMPORTANT: Always archive before deploying to production.**

```bash
# Archive current live version (REQUIRED)
ssh fischb@10.0.0.55 "cd /share/CACHEDEV1_DATA && tar -czf Web-archive/web-backup-\$(date +%Y%m%d-%H%M%S).tar.gz Web/"
```

Then deploy:
```powershell
.\deploy.ps1          # Interactive deployment
.\deploy.ps1 -Force   # Skip confirmation
.\deploy.ps1 -DryRun  # Preview what would deploy
```

The script:
- Uploads changed files to NAS
- Syncs asset directories: `sprites/`, `portraits/`, `images/`, `map/`
- Tests homepage loads
- Verifies Search API is responding
- Tests mailing list endpoint

**Archives stored at:** `/share/CACHEDEV1_DATA/Web-archive/`

### Asset Directories (auto-deployed)
These directories are synced in full during deployment:
- `sprites/` - Game icons (including `icons/*_new.png` for flip effects)
- `portraits/` - Character portraits (including `new/` subfolder for cycling)
- `images/` - General images
- `map/` - Deep zoom map tiles (`.dzi` + `_files/` folder)

**If new assets aren't showing:** Verify they exist on server:
```bash
ssh fischb@10.0.0.55 "ls /share/Web/sprites/icons/*_new*"
ssh fischb@10.0.0.55 "ls /share/Web/portraits/new/"
```

### 4. If API Fails After Deploy
```bash
ssh fischb@10.0.0.55 "bash /share/Web/api/start_api.sh"
```

---

## Project Overview

This is the Midwinter fan remaster website - a static site hosted on QNAP NAS (10.0.0.55) with a Flask API backend for AI-powered manual search.

---

## NAS Access

**SSH Connection:**
```bash
ssh fischb@10.0.0.55
```
Credentials: fischb / Arch3rD0g6074

**Web Files Location:** `/share/Web/`

**To deploy changes:**
```bash
scp <local-file> fischb@10.0.0.55:/share/Web/<path>
```

---

## Key Components

### 1. Static Pages
- `index.html` - Landing page
- `decisions.html` - Main navigation hub
- `characters.html` - Character roster
- `character_*.html` - Individual character pages (32 total)
- `enemies.html` - Enemy commanders
- `download.html` - Game downloads
- `search.html` - AI-powered manual search
- `recruit.html` - Mailing list signup
- `terrain.html`, `original.html`, `bevy.html` - Info pages

### 2. Flask Search API (`/share/Web/api/`)
- `search_api.py` - Claude-powered search with MCP tools
- `midwinter_unified.db` - SQLite database of manual content
- Runs in Docker container: `midwinter-search-api`
- Port: 8500 (internal)

### 3. Mailing List (`/share/Web/forms/`)
- `mailing-list.php` - Gmail SMTP handler
- Rate limited, logs to CSV

### 4. Cloudflare Tunnel
- Routes external traffic to NAS
- Auto-starts via `/share/CACHEDEV1_DATA/.qpkg/autorun/autorun.sh`

---

## Common Tasks

### Deploy Updated HTML
```bash
scp index.html fischb@10.0.0.55:/share/Web/
```

### Restart Flask API
```bash
ssh fischb@10.0.0.55 "bash /share/Web/api/start_api.sh"
```

### Check Cloudflared Status
```bash
ssh fischb@10.0.0.55 "ps aux | grep cloudflared"
ssh fischb@10.0.0.55 "tail -30 /share/homes/fischb/cloudflared.log"
```

### View Docker Containers
```bash
ssh fischb@10.0.0.55 "export DOCKER_HOST=unix:///var/run/system-docker.sock; /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker ps -a"
```

### Test Mailing Form
```bash
curl -X POST http://10.0.0.55/forms/mailing-list.php \
  -d "name=Test" -d "email=test@example.com" -d "role=fan"
```

---

## Update Download Links

When releasing a new version, update `download.html`:

1. Edit the version number in the header
2. Update all 4 download links (Windows, Mac Apple Silicon, Mac Intel, Linux)
3. Ensure release files exist in `/share/midwinter/releases/vX.Y.Z/`

---

## Design System

The website uses a retro/pixel aesthetic:

**Fonts:**
- Headers: `'Press Start 2P'` (pixel font)
- Body: `'IBM Plex Mono'` (monospace)

**Colors:**
```css
--bg-dark: #0a0a12;
--border-blue: #4a6b9a;
--border-light: #6a8bba;
--text-ice: #a8c8e8;
--text-white: #e8f0f8;
--accent-orange: #e87040;
--accent-yellow: #d4a840;
--tile-bg: #1a2030;
```

---

## Important Files

| File | Purpose |
|------|---------|
| `INFRASTRUCTURE.md` | Full system architecture documentation |
| `api/search_api.py` | Flask search API with Claude |
| `forms/mailing-list.php` | Email form handler |
| `nginx.conf` | Nginx config (reference only) |
| `sitemap.xml` | SEO sitemap |
| `robots.txt` | Crawler rules |

---

## DO NOT

- Modify credentials in committed files
- Push API keys to git
- Delete releases without backup
- Change cloudflared config without testing
- Restart Container Station (affects other services)

---

## Testing

**Local preview:** Open HTML files directly in browser

**Live test:** https://midwinter-remaster.titanium-helix.com

**API health:** `curl https://midwinter-remaster.titanium-helix.com/api-proxy/search.php -X POST -H "Content-Type: application/json" -d '{"query":"test"}'`
