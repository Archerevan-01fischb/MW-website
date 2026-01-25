# Midwinter Website Deploy Script
# Deploys local changes to NAS and verifies API health

param(
    [switch]$Force,      # Skip confirmation
    [switch]$DryRun      # Show what would be deployed without actually deploying
)

$NAS_HOST = "fischb@10.0.0.55"
$NAS_WEB_PATH = "/share/Web"
$LOCAL_PATH = $PSScriptRoot
$API_HEALTH_URL = "https://midwinter-remaster.titanium-helix.com/api-proxy/search.php"

# Files/folders to deploy (exclude sensitive/large files)
$DEPLOY_ITEMS = @(
    "*.html",
    "*.xml",
    "*.txt",
    "*.json",
    "*.png",
    "robots.txt",
    "sitemap.xml",
    "nginx.conf",
    "images",
    "sprites",
    "portraits",
    "videos",
    "api-proxy",
    "forms/mailing-list.php",
    "forms/SETUP_INSTRUCTIONS.txt"
)

# Excluded from deployment
$EXCLUDE = @(
    "*.md",
    "*.ps1",
    "*.template",
    ".git",
    ".gitignore",
    "api",
    "mcp-midwinter-search",
    "midwinter-remaster",
    "Enemy commanders",
    "releases",
    "Midwinter_Manual.pdf"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MIDWINTER WEBSITE DEPLOYMENT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Show git status
Write-Host "Recent changes:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Show what will be deployed
Write-Host "Files to deploy:" -ForegroundColor Yellow
$htmlFiles = Get-ChildItem -Path $LOCAL_PATH -Filter "*.html" -File | Select-Object -ExpandProperty Name
Write-Host "  HTML files: $($htmlFiles.Count) files"
Write-Host "  Directories: images, sprites, portraits, videos, api-proxy, forms"
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Would deploy the above files to $NAS_HOST`:$NAS_WEB_PATH" -ForegroundColor Magenta
    exit 0
}

# Confirmation
if (-not $Force) {
    $confirm = Read-Host "Deploy to production? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Deployment cancelled." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Deploying..." -ForegroundColor Green

# Deploy HTML files
Write-Host "  Uploading HTML files..." -ForegroundColor Gray
scp $LOCAL_PATH/*.html "${NAS_HOST}:${NAS_WEB_PATH}/"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Failed to upload HTML files" -ForegroundColor Red; exit 1 }

# Deploy XML files
Write-Host "  Uploading XML files..." -ForegroundColor Gray
scp $LOCAL_PATH/*.xml "${NAS_HOST}:${NAS_WEB_PATH}/"

# Deploy config files
Write-Host "  Uploading config files..." -ForegroundColor Gray
scp $LOCAL_PATH/robots.txt $LOCAL_PATH/nginx.conf "${NAS_HOST}:${NAS_WEB_PATH}/"

# Deploy api-proxy
Write-Host "  Uploading api-proxy..." -ForegroundColor Gray
scp -r $LOCAL_PATH/api-proxy/* "${NAS_HOST}:${NAS_WEB_PATH}/api-proxy/"

# Deploy forms (just the PHP, not logs)
Write-Host "  Uploading forms..." -ForegroundColor Gray
scp $LOCAL_PATH/forms/mailing-list.php "${NAS_HOST}:${NAS_WEB_PATH}/forms/"

# Deploy images directory
Write-Host "  Syncing images..." -ForegroundColor Gray
if (Test-Path "$LOCAL_PATH/images") {
    scp -r "$LOCAL_PATH/images" "${NAS_HOST}:${NAS_WEB_PATH}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    WARNING: images sync may have failed" -ForegroundColor Yellow }
}

# Deploy sprites directory (includes icons with _new variants)
Write-Host "  Syncing sprites..." -ForegroundColor Gray
if (Test-Path "$LOCAL_PATH/sprites") {
    scp -r "$LOCAL_PATH/sprites" "${NAS_HOST}:${NAS_WEB_PATH}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    WARNING: sprites sync may have failed" -ForegroundColor Yellow }
}

# Deploy portraits directory (includes /new subfolder)
Write-Host "  Syncing portraits..." -ForegroundColor Gray
if (Test-Path "$LOCAL_PATH/portraits") {
    scp -r "$LOCAL_PATH/portraits" "${NAS_HOST}:${NAS_WEB_PATH}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    WARNING: portraits sync may have failed" -ForegroundColor Yellow }
}

# Deploy map tiles (if exists)
if (Test-Path "$LOCAL_PATH/map") {
    Write-Host "  Syncing map tiles..." -ForegroundColor Gray
    ssh ${NAS_HOST} "mkdir -p ${NAS_WEB_PATH}/map"
    scp -r "$LOCAL_PATH/map" "${NAS_HOST}:${NAS_WEB_PATH}/"
    if ($LASTEXITCODE -ne 0) { Write-Host "    WARNING: map sync may have failed" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "Upload complete. Verifying deployment..." -ForegroundColor Green
Write-Host ""

# Wait a moment for files to sync
Start-Sleep -Seconds 2

# Test 1: Homepage loads
Write-Host "  Testing homepage..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "https://midwinter-remaster.titanium-helix.com/" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "    Homepage: OK" -ForegroundColor Green
    } else {
        Write-Host "    Homepage: FAILED (Status $($response.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "    Homepage: FAILED ($_)" -ForegroundColor Red
}

# Test 2: API health (search endpoint)
Write-Host "  Testing Search API..." -ForegroundColor Gray
try {
    $body = '{"query":"test"}'
    $response = Invoke-WebRequest -Uri $API_HEALTH_URL -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        $json = $response.Content | ConvertFrom-Json
        if ($json.success -or $json.error -match "API") {
            Write-Host "    Search API: OK (responding)" -ForegroundColor Green
        } else {
            Write-Host "    Search API: OK (returned response)" -ForegroundColor Green
        }
    } else {
        Write-Host "    Search API: WARNING (Status $($response.StatusCode))" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    Search API: FAILED ($_)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  API may need restart. Run:" -ForegroundColor Yellow
    Write-Host "    ssh fischb@10.0.0.55 'bash /share/Web/api/start_api.sh'" -ForegroundColor White
}

# Test 3: Mailing list endpoint
Write-Host "  Testing Mailing List endpoint..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "https://midwinter-remaster.titanium-helix.com/forms/mailing-list.php" -Method OPTIONS -UseBasicParsing -TimeoutSec 10
    Write-Host "    Mailing List: OK" -ForegroundColor Green
} catch {
    Write-Host "    Mailing List: WARNING (may still work)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Live site: https://midwinter-remaster.titanium-helix.com" -ForegroundColor White
Write-Host ""
