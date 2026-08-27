#!/usr/bin/env pwsh
#Requires -Version 5.1
<#
.SYNOPSIS
    Deploy AI Press Secretary to server from Windows computer
.DESCRIPTION
    1. Archives project
    2. Uploads to server via SCP
    3. Connects via SSH and runs installation
    4. Configures Nginx + SSL
.NOTES
    Run: .\deploy-simple.ps1
#>

[CmdletBinding()]
param(
    [string]$ServerIP = "31.28.9.200",
    [string]$Username = "root",
    [string]$Password = "123edcxzaqws",
    [string]$Domain = "press.my-dpr.ru",
    [string]$RemotePath = "/opt/pressa",
    [string]$LocalProjectPath = "C:\python\pressa",
    [int]$Port = 2324
)

Write-Host "=== AI Press Secretary Deployment ===" -ForegroundColor Green
Write-Host ""

# Check SSH/SCP
Write-Host "[1/6] Checking SSH and SCP..." -ForegroundColor Yellow
$ssh = Get-Command ssh -ErrorAction SilentlyContinue
$scp = Get-Command scp -ErrorAction SilentlyContinue

if (-not $ssh -or -not $scp) {
    Write-Host "ERROR: SSH or SCP not found!" -ForegroundColor Red
    Write-Host "Install OpenSSH Client: Settings -> Apps -> Optional Features -> OpenSSH Client"
    exit 1
}
Write-Host "OK" -ForegroundColor Green

# Create archive
Write-Host "[2/6] Creating project archive..." -ForegroundColor Yellow
$TempDir = "$env:TEMP\pressa-deploy-$(Get-Random)"
$ArchiveName = "pressa-deploy.tar.gz"
$ArchivePath = "$env:TEMP\$ArchiveName"

if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir | Out-Null

$ItemsToCopy = @("cabinet_service", "ai_core", "config.py", "requirements.txt", "deploy")
foreach ($item in $ItemsToCopy) {
    $src = Join-Path $LocalProjectPath $item
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $TempDir -Recurse -Force
    }
}

# Update domain in scripts
$nginxScript = Join-Path $TempDir "deploy\nginx-setup.sh"
if (Test-Path $nginxScript) {
    $content = [System.IO.File]::ReadAllText($nginxScript)
    $content = $content.Replace("твой_домен.com", $Domain)
    [System.IO.File]::WriteAllText($nginxScript, $content)
}

$sslScript = Join-Path $TempDir "deploy\ssl-setup.sh"
if (Test-Path $sslScript) {
    $content = [System.IO.File]::ReadAllText($sslScript)
    $content = $content.Replace("твой_домен.com", $Domain)
    $content = $content.Replace("твой_email@example.com", "admin@$Domain")
    [System.IO.File]::WriteAllText($sslScript, $content)
}

# Create archive
Set-Location $env:TEMP
$tar = Get-Command tar -ErrorAction SilentlyContinue
if ($tar) {
    tar -czf $ArchiveName -C $TempDir .
} else {
    Compress-Archive -Path "$TempDir\*" -DestinationPath "$env:TEMP\pressa-deploy.zip" -Force
    $ArchiveName = "pressa-deploy.zip"
    $ArchivePath = "$env:TEMP\$ArchiveName"
}

$size = [math]::Round((Get-Item $ArchivePath).Length / 1MB, 1)
Write-Host "Archive created: $ArchivePath ($size MB)" -ForegroundColor Green

# Upload to server
Write-Host "[3/6] Uploading to server ${ServerIP}:${Port}..." -ForegroundColor Yellow
$sshOptions = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p $Port"

# Create directory
$createDir = "mkdir -p $RemotePath && rm -rf $RemotePath/*"
$createDir | ssh $sshOptions ${Username}@${ServerIP} "bash -s" 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to server!" -ForegroundColor Red
    Write-Host "Check: IP address, login, password, port $Port" -ForegroundColor Yellow
    exit 1
}
Write-Host "Connected" -ForegroundColor Green

# Upload archive
scp $sshOptions $ArchivePath "${Username}@${ServerIP}:${RemotePath}/" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Upload failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Uploaded" -ForegroundColor Green

# Extract and install
Write-Host "[4/6] Installing on server (this takes 5-10 minutes)..." -ForegroundColor Yellow
$installScript = @"
cd $RemotePath

# Extract
if [ -f "$ArchiveName" ]; then
    tar -xzf "$ArchiveName"
    rm "$ArchiveName"
elif [ -f "pressa-deploy.zip" ]; then
    apt-get install -y unzip >/dev/null 2>&1
    unzip -q "pressa-deploy.zip"
    rm "pressa-deploy.zip"
fi

# Fix directory structure
if [ ! -d "cabinet_service" ]; then
    for dir in */; do
        if [ -d "\$dir/cabinet_service" ]; then
            mv "\$dir"/* .
            rm -rf "\$dir"
            break
        fi
    done
fi

# Make scripts executable
chmod +x deploy/*.sh

# Run install
cd deploy
./install.sh
"@

$installScript | ssh $sshOptions ${Username}@${ServerIP} "bash -s" 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Installation may have errors. Check logs on server." -ForegroundColor Yellow
}

# Configure Nginx and SSL
Write-Host "[5/6] Configuring Nginx and SSL..." -ForegroundColor Yellow
$nginxScript = @"
cd $RemotePath/deploy
sed -i "s/твой_домен.com/$Domain/g" nginx-setup.sh
./nginx-setup.sh
sed -i "s/твой_домен.com/$Domain/g" ssl-setup.sh
sed -i "s/твой_email@example.com/admin@$Domain/g" ssl-setup.sh
./ssl-setup.sh
"@

$nginxScript | ssh $sshOptions ${Username}@${ServerIP} "bash -s" 2>$null

# Cleanup
Write-Host "[6/6] Cleaning up..." -ForegroundColor Yellow
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }
Set-Location $LocalProjectPath

# Final message
Write-Host ""
Write-Host "=== Deployment Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Website: https://$Domain" -ForegroundColor Cyan
Write-Host "Project: $RemotePath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure .env file:" -ForegroundColor White
Write-Host "   ssh ${Username}@${ServerIP}" -ForegroundColor Gray
Write-Host "   nano $RemotePath/.env" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Fill in API keys (BOT_TOKEN, PIAPI_API_KEY, etc.)" -ForegroundColor White
Write-Host ""
Write-Host "3. Restart service:" -ForegroundColor White
Write-Host "   systemctl restart pressa" -ForegroundColor Gray
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "   ssh ${Username}@${ServerIP}" -ForegroundColor Gray
Write-Host "   sudo systemctl status pressa" -ForegroundColor Gray
Write-Host "   sudo journalctl -u pressa -f" -ForegroundColor Gray