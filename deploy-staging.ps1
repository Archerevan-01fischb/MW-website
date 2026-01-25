# Midwinter Website - Staging Deployment Script
# Deploys to staging.midwinter-remaster.titanium-helix.com

param(
    [switch]$Force,
    [switch]$DryRun
)

$NAS_USER = "fischb"
$NAS_HOST = "10.0.0.55"
$STAGING_PATH = "/share/Web-staging"
$LOCAL_PATH = $PSScriptRoot

# Files and directories to deploy
$DEPLOY_ITEMS = @(
    "*.html",
    "*.css",
    "*.js",
    "*.xml",
    "*.txt",
    "*.pdf",
    "*.ico",
    "portraits",
    "sprites",
    "images",
    "videos",
    "fonts",
    "forms",
    "api-proxy",
    "map",
    "surrender-decision.png"
)

# Files to exclude
$EXCLUDE = @(
    "deploy*.ps1",
    ".git",
    ".mcp.json",
    "CLAUDE.md",
    "INFRASTRUCTURE.md",
    "*.jsonl",
    "node_modules",
    "mcp-midwinter-search",
    "database"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MIDWINTER STAGING DEPLOYMENT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: staging.midwinter-remaster.titanium-helix.com" -ForegroundColor Yellow
Write-Host "NAS Path: $NAS_HOST`:$STAGING_PATH" -ForegroundColor Yellow
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be uploaded" -ForegroundColor Magenta
    Write-Host ""
}

# Build exclude arguments for scp/rsync
$excludeArgs = ($EXCLUDE | ForEach-Object { "--exclude='$_'" }) -join " "

# Confirmation
if (-not $Force -and -not $DryRun) {
    $response = Read-Host "Deploy to STAGING? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Deployment cancelled." -ForegroundColor Red
        exit 0
    }
}

Write-Host ""
Write-Host "Deploying files to staging..." -ForegroundColor Green

if ($DryRun) {
    Write-Host "[DRY RUN] Would sync files to $NAS_HOST`:$STAGING_PATH" -ForegroundColor Magenta
} else {
    # Use rsync for efficient sync (if available) or fall back to scp
    $rsyncAvailable = $false
    try {
        $null = Get-Command rsync -ErrorAction Stop
        $rsyncAvailable = $true
    } catch {
        $rsyncAvailable = $false
    }

    if ($rsyncAvailable) {
        # Use rsync for efficient delta sync
        $rsyncCmd = "rsync -avz --delete --progress $excludeArgs '$LOCAL_PATH/' '${NAS_USER}@${NAS_HOST}:${STAGING_PATH}/'"
        Write-Host "Using rsync..." -ForegroundColor Gray
        Invoke-Expression $rsyncCmd
    } else {
        # Fall back to scp for each item
        Write-Host "Using scp (rsync not available)..." -ForegroundColor Gray

        foreach ($item in $DEPLOY_ITEMS) {
            $paths = Get-ChildItem -Path $LOCAL_PATH -Name $item -ErrorAction SilentlyContinue
            foreach ($path in $paths) {
                $fullPath = Join-Path $LOCAL_PATH $path
                if (Test-Path $fullPath) {
                    $isDir = (Get-Item $fullPath).PSIsContainer
                    if ($isDir) {
                        Write-Host "  Uploading directory: $path" -ForegroundColor Gray
                        scp -r "$fullPath" "${NAS_USER}@${NAS_HOST}:${STAGING_PATH}/"
                    } else {
                        Write-Host "  Uploading: $path" -ForegroundColor Gray
                        scp "$fullPath" "${NAS_USER}@${NAS_HOST}:${STAGING_PATH}/"
                    }
                }
            }
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  STAGING DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Preview at: https://staging.midwinter-remaster.titanium-helix.com" -ForegroundColor Cyan
Write-Host ""

# Test staging site
if (-not $DryRun) {
    Write-Host "Testing staging site..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "https://staging.midwinter-remaster.titanium-helix.com" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "  Staging site is accessible" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Warning: Could not reach staging site (DNS may need time to propagate)" -ForegroundColor Yellow
    }
}
