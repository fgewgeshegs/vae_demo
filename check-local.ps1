$ErrorActionPreference = "Continue"
$runtimeDir = Join-Path $PSScriptRoot ".runtime"
$dockerConfigDir = Join-Path $runtimeDir "docker-config"
New-Item -ItemType Directory -Force -Path $dockerConfigDir | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $dockerConfigDir "config.json"))) {
    Set-Content -LiteralPath (Join-Path $dockerConfigDir "config.json") -Value "{}"
}
$env:DOCKER_CONFIG = $dockerConfigDir

$checks = @(
    @{ Name = "Frontend"; Url = "http://127.0.0.1:5173" },
    @{ Name = "Backend"; Url = "http://127.0.0.1:8000/health" },
    @{ Name = "Inference"; Url = "http://127.0.0.1:8100/health" }
)

$failed = $false
foreach ($check in $checks) {
    try {
        $response = Invoke-RestMethod -Uri $check.Url -TimeoutSec 10
        $status = if ($response.status) { $response.status } else { "reachable" }
        Write-Host ("[OK]   {0}: {1}" -f $check.Name, $status) -ForegroundColor Green
    }
    catch {
        $failed = $true
        Write-Host ("[FAIL] {0}: {1}" -f $check.Name, $_.Exception.Message) -ForegroundColor Red
    }
}

try {
    $containers = docker compose -f (Join-Path $PSScriptRoot "docker-compose.yml") ps --format json | ConvertFrom-Json
    foreach ($container in $containers) {
        Write-Host ("[INFO] Docker {0}: {1}" -f $container.Service, $container.State)
    }
}
catch {
    $failed = $true
    Write-Host "[FAIL] Docker is unavailable. Start Docker Desktop, then run start-local.cmd." -ForegroundColor Red
}

if ($failed) { exit 1 }
