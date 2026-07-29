$runtimeDir = Join-Path $PSScriptRoot ".runtime"

foreach ($name in @("frontend", "backend", "inference")) {
    $pidFile = Join-Path $runtimeDir "$name.pid"

    if (Test-Path -LiteralPath $pidFile) {
        $processId = Get-Content $pidFile

        try {
            Write-Host "Stopping $name (PID $processId)..."
            taskkill /PID $processId /T /F | Out-Null
            Write-Host "Stopped $name"
        }
        catch {
            Write-Warning "Failed to stop $name"
        }

        Remove-Item -LiteralPath $pidFile -Force
    }
}

Write-Host "PostgreSQL and Redis containers were left running to preserve quick startup."
