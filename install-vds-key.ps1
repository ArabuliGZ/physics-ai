$ErrorActionPreference = "Stop"

$publicKeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519.pub"

if (-not (Test-Path $publicKeyPath)) {
    throw "SSH public key not found: $publicKeyPath"
}

Write-Host "==> Installing local SSH public key on VDS"
Write-Host "==> The server will ask for the root password one last time."

Get-Content $publicKeyPath |
    ssh root@104.171.131.247 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

Write-Host "==> Checking passwordless login"
ssh -o BatchMode=yes physics-ai-vds "echo key-ok"

Write-Host "==> Done. Now deploy with: .\deploy-vds.ps1"
