param(
    [string]$OutDir = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados",
    [string]$DateTag = $(Get-Date -Format 'yyyyMMdd'),
    [string]$EnvFile = $(Join-Path $PSScriptRoot 'jira_env.txt'),
    [int]$Workers = 8,
    [bool]$RunPortfolioExport = $true,
    [bool]$RunMetrics = $true,
    [bool]$OpenDashboard = $true
)

$ErrorActionPreference = 'Stop'

function Import-EnvFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) {
            return
        }

        $parts = $line.Split('=', 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")

        if ($key -and $value -and -not (Test-Path "Env:$key")) {
            Set-Item -Path "Env:$key" -Value $value
        }
    }
}

Import-EnvFile -Path $EnvFile

if (-not $env:JIRA_BASE_URL -or -not $env:JIRA_EMAIL -or -not $env:JIRA_API_TOKEN) {
    throw "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN (ou preencha o arquivo $EnvFile) antes de executar."
}

$scriptPath = Join-Path $PSScriptRoot 'jira_to_pipeline_csv.py'
$portfolioScript = Join-Path $PSScriptRoot 'jira_portfolio_to_csv.py'
if (-not (Test-Path $scriptPath)) {
    throw "Arquivo não encontrado: $scriptPath"
}
$metricsScript = Join-Path $PSScriptRoot 'dash_board_metricas.py'
$dashboardScript = Join-Path $PSScriptRoot 'dashboard_full.py'

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

# Ajuste as chaves Jira se necessário.
$projects = @(
    @{ Key = 'W1NNR'; FilePrefix = 'w1nner-downstream' },
    @{ Key = 'S1NC'; FilePrefix = 's1nc-downstream' },
    @{ Key = 'BF'; FilePrefix = 'befinance-downstream' },
    @{ Key = 'DT'; FilePrefix = 'dataanalytics-downstream' }
)

Write-Host "Iniciando exportação Jira -> CSV..." -ForegroundColor Cyan
Write-Host "Base URL: $($env:JIRA_BASE_URL)"
Write-Host "Saída: $OutDir"
Write-Host "Data: $DateTag"

foreach ($p in $projects) {
    $outFile = Join-Path $OutDir ("{0}-{1}-data.csv" -f $p.FilePrefix, $DateTag)

    Write-Host "`nProjeto: $($p.Key)" -ForegroundColor Yellow
    Write-Host "Arquivo: $outFile"

    & python $scriptPath --projects $p.Key --out $outFile --env-file $EnvFile --workers $Workers
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na exportação do projeto $($p.Key)."
    }

    $bottleneckOut = Join-Path $OutDir ("{0}-{1}-data_bottlenecks.csv" -f $p.FilePrefix, $DateTag)
    $bottleneckLatest = Join-Path $OutDir ("{0}-latest-data_bottlenecks.csv" -f $p.FilePrefix)
    if (Test-Path $bottleneckOut) {
        Copy-Item -Path $bottleneckOut -Destination $bottleneckLatest -Force
        Write-Host "Arquivo latest atualizado: $bottleneckLatest" -ForegroundColor Green
    }
}

Write-Host "`nExportações concluídas com sucesso." -ForegroundColor Green

if ($RunPortfolioExport) {
    if (-not (Test-Path $portfolioScript)) {
        throw "Arquivo não encontrado: $portfolioScript"
    }

    $portfolioOut = Join-Path $OutDir ("portfolio-bt-ns-{0}-data.csv" -f $DateTag)
    Write-Host "`nExportando CSV de portfólio (BT/NS)..." -ForegroundColor Cyan
    Write-Host "Arquivo: $portfolioOut"

    & python $portfolioScript --projects BT NS --out $portfolioOut --env-file $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na exportação do portfólio (BT/NS)."
    }

    $portfolioLatest = Join-Path $OutDir "portfolio-bt-ns-latest-data.csv"
    Copy-Item -Path $portfolioOut -Destination $portfolioLatest -Force
    Write-Host "Arquivo latest atualizado: $portfolioLatest" -ForegroundColor Green
}

if ($RunMetrics) {
    Write-Host "`nExecutando processamento de métricas..." -ForegroundColor Cyan
    if (-not (Test-Path $metricsScript)) {
        throw "Arquivo não encontrado: $metricsScript"
    }

    $env:DATA_FOLDER = $OutDir
    $env:FLOW_PMO_DATA_DIR = $OutDir
    & python $metricsScript
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar o processamento de métricas."
    }
}

if ($OpenDashboard) {
    Write-Host "`nIniciando dashboard web..." -ForegroundColor Cyan
    if (-not (Test-Path $dashboardScript)) {
        throw "Arquivo não encontrado: $dashboardScript"
    }

    Start-Process -FilePath "python" -ArgumentList "`"$dashboardScript`"" -WorkingDirectory $PSScriptRoot | Out-Null
    Start-Sleep -Seconds 6
    Start-Process "http://127.0.0.1:8050" | Out-Null
    Write-Host "Dashboard aberto em http://127.0.0.1:8050" -ForegroundColor Green
}
