param(
    [string]$OutDir = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados",
    [string]$DateTag = $(Get-Date -Format 'yyyyMMdd'),
    [string]$EnvFile = $(Join-Path $PSScriptRoot 'jira_env.txt'),
    [int]$Workers = 8,
    [bool]$RunDetailedChangelogExport = $false,
    [bool]$RunPortfolioExport = $true,
    [bool]$RunMetrics = $true,
    [bool]$OpenDashboard = $true
)

$ErrorActionPreference = 'Stop'

function Import-EnvFile {
    param(
        [string]$Path,
        [bool]$OverrideExisting = $true
    )

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

        if ($key -and $value -and ($OverrideExisting -or -not (Test-Path "Env:$key"))) {
            Set-Item -Path "Env:$key" -Value $value
        }
    }
}

Import-EnvFile -Path $EnvFile -OverrideExisting $true

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
$latestDirDefault = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest"
$latestDir = if ($env:FLOW_PMO_LATEST_DIR) { $env:FLOW_PMO_LATEST_DIR } else { $latestDirDefault }

function Publish-LatestArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$LatestDir
    )

    if (-not (Test-Path $SourcePath)) {
        return
    }

    $targetPath = Join-Path $LatestDir (Split-Path -Path $SourcePath -Leaf)
    Copy-Item -Path $SourcePath -Destination $targetPath -Force
    Write-Host "Alias latest publicado em: $targetPath" -ForegroundColor Green
}

function Sync-LatestArtifactsFromOutDir {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$LatestDir
    )

    $latestFiles = Get-ChildItem -Path $SourceDir -File | Where-Object { $_.Name -match 'latest' }
    foreach ($f in $latestFiles) {
        Publish-LatestArtifact -SourcePath $f.FullName -LatestDir $LatestDir
    }
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}
if (-not (Test-Path $latestDir)) {
    New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
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

# The downstream exporter resolves workflow by project/type.
# Ignore global JIRA_STATUS_MAP here to avoid forcing one flow for all projects.
$originalJiraStatusMap = $env:JIRA_STATUS_MAP
if ($env:JIRA_STATUS_MAP) {
    Write-Host "Ignorando JIRA_STATUS_MAP global durante exportação downstream (fluxo por projeto habilitado)." -ForegroundColor DarkYellow
}
Remove-Item -Path Env:JIRA_STATUS_MAP -ErrorAction SilentlyContinue
$env:JIRA_IGNORE_STATUS_MAP = '1'

foreach ($p in $projects) {
    $outFile = Join-Path $OutDir ("{0}-{1}-data.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogOut = Join-Path $OutDir ("{0}-{1}-data_detailed_changelog.csv" -f $p.FilePrefix, $DateTag)

    Write-Host "`nProjeto: $($p.Key)" -ForegroundColor Yellow
    Write-Host "Arquivo: $outFile"

    $exportArgs = @(
        $scriptPath,
        '--projects', $p.Key,
        '--out', $outFile,
        '--env-file', $EnvFile,
        '--workers', $Workers
    )
    if ($RunDetailedChangelogExport) {
        $exportArgs += @('--detailed-changelog-out', $detailedChangelogOut)
        Write-Host "Changelog detalhado: $detailedChangelogOut"
    }

    & python @exportArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na exportação do projeto $($p.Key)."
    }

    $downstreamLatest = Join-Path $OutDir ("{0}-latest-data.csv" -f $p.FilePrefix)
    if (Test-Path $outFile) {
        Copy-Item -Path $outFile -Destination $downstreamLatest -Force
        Write-Host "Arquivo latest atualizado: $downstreamLatest" -ForegroundColor Green
        Publish-LatestArtifact -SourcePath $downstreamLatest -LatestDir $latestDir
    }

    $bottleneckOut = Join-Path $OutDir ("{0}-{1}-data_bottlenecks.csv" -f $p.FilePrefix, $DateTag)
    $bottleneckLatest = Join-Path $OutDir ("{0}-latest-data_bottlenecks.csv" -f $p.FilePrefix)
    if (Test-Path $bottleneckOut) {
        Copy-Item -Path $bottleneckOut -Destination $bottleneckLatest -Force
        Write-Host "Arquivo latest atualizado: $bottleneckLatest" -ForegroundColor Green
        Publish-LatestArtifact -SourcePath $bottleneckLatest -LatestDir $latestDir
    }

    if ($RunDetailedChangelogExport -and (Test-Path $detailedChangelogOut)) {
        $detailedChangelogLatest = Join-Path $OutDir ("{0}-latest-data_detailed_changelog.csv" -f $p.FilePrefix)
        Copy-Item -Path $detailedChangelogOut -Destination $detailedChangelogLatest -Force
        Write-Host "Arquivo latest atualizado: $detailedChangelogLatest" -ForegroundColor Green
        Publish-LatestArtifact -SourcePath $detailedChangelogLatest -LatestDir $latestDir
    }
}

if ($null -ne $originalJiraStatusMap -and $originalJiraStatusMap -ne '') {
    $env:JIRA_STATUS_MAP = $originalJiraStatusMap
}
Remove-Item -Path Env:JIRA_IGNORE_STATUS_MAP -ErrorAction SilentlyContinue

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
    Publish-LatestArtifact -SourcePath $portfolioLatest -LatestDir $latestDir
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
    Sync-LatestArtifactsFromOutDir -SourceDir $OutDir -LatestDir $latestDir
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
