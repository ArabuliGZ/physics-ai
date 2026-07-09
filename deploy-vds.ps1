$ErrorActionPreference = "Stop"

Write-Host "==> Push local commits to GitHub"
git push

Write-Host "==> Deploy on VDS"
ssh physics-ai-vds "/var/www/physics-ai/deploy.sh"

Write-Host "==> Done"
