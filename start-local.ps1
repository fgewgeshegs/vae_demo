$ErrorActionPreference = "Stop"

$projectDir = $PSScriptRoot
$backendDir = Join-Path $projectDir "backend"
$frontendDir = Join-Path $projectDir "frontend"
$runtimeDir = Join-Path $projectDir ".runtime"
$bgePython = "D:\jay_demo\bge_env\Scripts\python.exe"
$dockerConfigDir = Join-Path $runtimeDir "docker-config"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $dockerConfigDir | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $dockerConfigDir "config.json"))) {
    Set-Content -LiteralPath (Join-Path $dockerConfigDir "config.json") -Value "{}"
}
$env:DOCKER_CONFIG = $dockerConfigDir

function Test-Http([string]$Url) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Stop-ProcessOnPort([int]$Port) {
    Write-Host "Checking port $Port for existing processes..."
    try {
        $pids = @()
        try {
            $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction Stop | Where-Object { $_.State -eq 'Listen' }
            $pids += $conn | Select-Object -ExpandProperty OwningProcess
        }
        catch {
            $lines = netstat -ano | Select-String ":$Port\s"
            $pids += $lines | ForEach-Object { ($_ -split '\s+')[-1] }
        }
        $pids = $pids | Where-Object { $_ -gt 0 } | Select-Object -Unique
        foreach ($pid in $pids) {
            try {
                $proc = Get-Process -Id $pid -ErrorAction Stop
                Write-Host "  Killing $($proc.ProcessName) (PID $pid)" -ForegroundColor Yellow
                Stop-Process -Id $pid -Force
                Start-Sleep -Milliseconds 500
            }
            catch {
                Write-Warning "PID $pid exists in TCP table but process was not found."
            }
        }
        Start-Sleep -Seconds 1

        $remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($remaining) {
            Write-Warning "Port $Port is still occupied after cleanup."
        }
    }
    catch {
        Write-Warning "Could not clean port ${Port}: $_"
    }
}

function Wait-Http([string]$Name, [string]$Url, [int]$Seconds) {
    Write-Host "Waiting for $Name..."
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-Http $Url) {
            Write-Host "$Name is ready." -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "$Name did not become ready. Check logs in $runtimeDir"
}

function Test-Docker {
    & docker info 1>$null 2>$null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path -LiteralPath $bgePython)) {
    throw "BGE Python not found: $bgePython"
}

$env:HF_HOME = "D:\jay_demo\models"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"

if (-not (Test-Docker)) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
        throw "Docker Desktop is unavailable. Install or start Docker Desktop, then retry."
    }
    Write-Host "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop | Out-Null
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Docker) { break }
    }
    if (-not (Test-Docker)) {
        throw "Docker Desktop did not become ready within 120 seconds."
    }
}

Push-Location $projectDir
try {
    docker compose up -d postgres redis
}
finally {
    Pop-Location
}

Stop-ProcessOnPort 8100
if (-not (Test-Http "http://127.0.0.1:8100/health")) {
    $inference = Start-Process -FilePath $bgePython `
        -ArgumentList "-m", "uvicorn", "inference_service.app:app", "--host", "127.0.0.1", "--port", "8100" `
        -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "inference.log") `
        -RedirectStandardError (Join-Path $runtimeDir "inference-error.log")
    $inference.Id | Set-Content (Join-Path $runtimeDir "inference.pid")
}
Wait-Http "Inference service" "http://127.0.0.1:8100/health" 120

Stop-ProcessOnPort 8000
if (-not (Test-Http "http://127.0.0.1:8000/health")) {
    $env:BGE_INFERENCE_SERVICE_URL = "http://127.0.0.1:8100"
    $backend = Start-Process -FilePath $bgePython `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "backend.log") `
        -RedirectStandardError (Join-Path $runtimeDir "backend-error.log")
    $backend.Id | Set-Content (Join-Path $runtimeDir "backend.pid")
}
Wait-Http "Backend" "http://127.0.0.1:8000/health" 120

Stop-ProcessOnPort 5173
if (-not (Test-Http "http://127.0.0.1:5173")) {
    $frontend = Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run", "dev", "--", "--host", "127.0.0.1" `
        -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "frontend.log") `
        -RedirectStandardError (Join-Path $runtimeDir "frontend-error.log")
    $frontend.Id | Set-Content (Join-Path $runtimeDir "frontend.pid")
}
Wait-Http "Frontend" "http://127.0.0.1:5173" 60

Write-Host ""
Write-Host "Project is ready: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "Run check-local.cmd for diagnostics or stop-local.cmd to stop local processes."
