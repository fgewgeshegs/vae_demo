$ErrorActionPreference = "Stop"

$projectDir = $PSScriptRoot
$workspaceDir = Split-Path $projectDir -Parent

$requiredPaths = @(
    (Join-Path $workspaceDir "models\bge-m3\config.json"),
    (Join-Path $workspaceDir "models\bge-reranker-v2-m3\config.json"),
    (Join-Path $workspaceDir "knowledge-base\embeddings\metadata.json"),
    (Join-Path $workspaceDir "knowledge-base\db\faiss.index")
)

$missingPaths = @($requiredPaths | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missingPaths.Count -gt 0) {
    Write-Host "Required model or knowledge-base files are missing:" -ForegroundColor Red
    $missingPaths | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Copy the models and knowledge-base directories beside vae_demo, then run this script again."
    exit 1
}

Push-Location $projectDir
try {
    docker compose up --build
}
finally {
    Pop-Location
}
