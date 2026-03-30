# COLLEAGUE_AUTO_PREP.ps1
# This script checks and installs Git, Node.js, and FFmpeg using winget.

$ErrorActionPreference = "Stop"

function Write-Host-Cyan($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Host-Green($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Host-Yellow($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Host-Red($msg) { Write-Host $msg -ForegroundColor Red }

Write-Host-Cyan "=========================================="
Write-Host-Cyan "   System Dependency Auto-Preparation     "
Write-Host-Cyan "=========================================="

# 1. Check for winget
Write-Host "Checking for winget..."
try {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (!$winget) {
        Write-Host-Red "[ERROR] winget not found. Please ensure you are on Windows 10/11 with latest updates."
        exit 1
    }
} catch {
    Write-Host-Red "[ERROR] Failed to find winget."
    exit 1
}

$needsRestart = $false

# 2. Check and Install Git
Write-Host "Checking for Git..."
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host-Yellow "[MISSING] Git. Installing via winget..."
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    $needsRestart = $true
} else {
    Write-Host-Green "[OK] Git is already installed."
}

# 3. Check and Install Node.js
Write-Host "Checking for Node.js (for PM2)..."
if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host-Yellow "[MISSING] Node.js. Installing via winget..."
    winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
    $needsRestart = $true
} else {
    Write-Host-Green "[OK] Node.js is already installed."
}

# 4. Check and Install FFmpeg
Write-Host "Checking for FFmpeg..."
if (!(Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host-Yellow "[MISSING] FFmpeg. Installing via winget..."
    # Gyan.FFmpeg is the most common and robust build on winget
    winget install --id Gyan.FFmpeg -e --source winget --accept-package-agreements --accept-source-agreements
    $needsRestart = $true
} else {
    Write-Host-Green "[OK] FFmpeg is already installed."
}

Write-Host-Cyan "=========================================="
if ($needsRestart) {
    Write-Host-Yellow "System components were installed. "
    Write-Host-Yellow "Please RESTART your terminal/CMD after this script finishes to apply PATH changes."
} else {
    Write-Host-Green "All system prerequisites met!"
}
Write-Host-Cyan "=========================================="
