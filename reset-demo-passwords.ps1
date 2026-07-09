$ErrorActionPreference = "Stop"

Write-Host "==> Reset demo passwords on VDS"

ssh physics-ai-vds "cd /var/www/physics-ai && ./venv/bin/python -c 'from app.demo_seed import reset_demo_passwords; print(reset_demo_passwords())'"

Write-Host "==> Done. Demo password is: test"
