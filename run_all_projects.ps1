param(
    [string]$OutDir = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados",
    [string]$DateTag = $(Get-Date -Format 'yyyyMMdd'),
    [string]$EnvFile = $(Join-Path $PSScriptRoot 'jira_env.txt'),
    [int]$Workers = 8,
    [bool]$RunDetailedChangelogExport = $false,
    [bool]$RunPortfolioExport = $true,
    [bool]$RunGmudCoverage = $true,
    [bool]$RunCapexExport = $true,
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
$gmudCoverageScript = Join-Path $PSScriptRoot 'jira_gmud_coverage.py'
$capexScript = Join-Path $PSScriptRoot 'jira_capex_monthly.py'
if (-not (Test-Path $scriptPath)) {
    throw "Arquivo não encontrado: $scriptPath"
}
$metricsScript = Join-Path $PSScriptRoot 'dash_board_metricas.py'
$dashboardScript = Join-Path $PSScriptRoot 'dashboard_full.py'
$copyLatestUploadScript = Join-Path $PSScriptRoot 'copy_latest_upload.py'
$latestDirDefault = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest"
$latestDir = if ($env:FLOW_PMO_LATEST_DIR) { $env:FLOW_PMO_LATEST_DIR } else { $latestDirDefault }
$gmudChgJql = if ($env:FLOW_PMO_GMUD_CHG_JQL) { $env:FLOW_PMO_GMUD_CHG_JQL } else { 'project = CHG ORDER BY status ASC, created DESC' }
$jiraBitbucketCommitDepth = if ($env:FLOW_PMO_JIRA_BB_COMMIT_DEPTH) { $env:FLOW_PMO_JIRA_BB_COMMIT_DEPTH } else { '250' }
$jiraBitbucketMinIntervalMs = if ($env:FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS) { $env:FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS } else { '750' }
$dtBoardJql = 'project in (10290) AND issuetype in (10254, 10255,10258, 10257,Bug,Ad-hoc) ORDER BY Rank ASC'

function Get-ProjectBitbucketRepos {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectKey
    )

    switch ($ProjectKey.ToUpperInvariant()) {
        'W1NNR' { return 'w1nner' }
        'S1NC' { return 'w1nner' }
        'BF' { return 'be-finance-api,be-finance-web,be-finance-lambda,be-finance-diagnostic-api,be-finance-diagnostic-web,be-finance-dev' }
        'DT' { return 'd-a-analysis,w1-data-toolbox,automacao-rfv,apuracao-indicadores-mensais,api-resumo-e-insights,c3po-automation' }
        default { return '' }
    }
}

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

function Update-LatestUploadPackage {
    if (-not (Test-Path $copyLatestUploadScript)) {
        throw "Arquivo não encontrado: $copyLatestUploadScript"
    }

    & python $copyLatestUploadScript --source-dir $latestDir --dest-dir (Join-Path $latestDir 'latest-upload') --clean-dest
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao atualizar a pasta latest-upload."
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
    @{ Key = 'W1NNR'; FilePrefix = 'w1nner-downstream'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'W1NNR') },
    @{ Key = 'S1NC'; FilePrefix = 's1nc-downstream'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'S1NC') },
    @{ Key = 'BF'; FilePrefix = 'befinance-downstream'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'BF') },
    @{ Key = 'DT'; FilePrefix = 'dataanalytics-downstream'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'DT'); Jql = $dtBoardJql }
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
$originalBbRepos = $env:BB_REPOS
$originalBbRepo = $env:BB_REPO
$originalBbCommitDepth = $env:BB_COMMIT_DEPTH
$originalBbMinIntervalMs = $env:BB_MIN_REQUEST_INTERVAL_MS

foreach ($p in $projects) {
    $outFile = Join-Path $OutDir ("{0}-{1}-data.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogOut = Join-Path $OutDir ("{0}-{1}-data_detailed_changelog.csv" -f $p.FilePrefix, $DateTag)

    Write-Host "`nProjeto: $($p.Key)" -ForegroundColor Yellow
    Write-Host "Arquivo: $outFile"

    if ($p.BitbucketRepos) {
        $env:BB_REPOS = $p.BitbucketRepos
        $env:BB_REPO = ($p.BitbucketRepos -split ',')[0]
        $env:BB_COMMIT_DEPTH = $jiraBitbucketCommitDepth
        $env:BB_MIN_REQUEST_INTERVAL_MS = $jiraBitbucketMinIntervalMs
        Write-Host "Bitbucket escopado para o projeto: $($env:BB_REPOS) | depth=$($env:BB_COMMIT_DEPTH) | intervalo=$($env:BB_MIN_REQUEST_INTERVAL_MS)ms" -ForegroundColor DarkYellow
    }

    $exportArgs = @(
        $scriptPath,
        '--projects', $p.Key,
        '--out', $outFile,
        '--env-file', $EnvFile,
        '--workers', $Workers,
        '--skip-devexecutor-bitbucket'
    )
    if ($p.Jql) {
        $exportArgs += @('--jql', $p.Jql)
        Write-Host "Usando JQL dedicada do projeto: $($p.Jql)" -ForegroundColor DarkCyan
    }
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
if ($null -ne $originalBbRepos -and $originalBbRepos -ne '') {
    $env:BB_REPOS = $originalBbRepos
} else {
    Remove-Item -Path Env:BB_REPOS -ErrorAction SilentlyContinue
}
if ($null -ne $originalBbRepo -and $originalBbRepo -ne '') {
    $env:BB_REPO = $originalBbRepo
} else {
    Remove-Item -Path Env:BB_REPO -ErrorAction SilentlyContinue
}
if ($null -ne $originalBbCommitDepth -and $originalBbCommitDepth -ne '') {
    $env:BB_COMMIT_DEPTH = $originalBbCommitDepth
} else {
    Remove-Item -Path Env:BB_COMMIT_DEPTH -ErrorAction SilentlyContinue
}
if ($null -ne $originalBbMinIntervalMs -and $originalBbMinIntervalMs -ne '') {
    $env:BB_MIN_REQUEST_INTERVAL_MS = $originalBbMinIntervalMs
} else {
    Remove-Item -Path Env:BB_MIN_REQUEST_INTERVAL_MS -ErrorAction SilentlyContinue
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
    Publish-LatestArtifact -SourcePath $portfolioLatest -LatestDir $latestDir
}

if ($RunGmudCoverage) {
    if (-not (Test-Path $gmudCoverageScript)) {
        throw "Arquivo não encontrado: $gmudCoverageScript"
    }

    $gmudSummaryOut = Join-Path $OutDir ("gmud-coverage-index-{0}.csv" -f $DateTag)
    $gmudWeeklyOut = Join-Path $OutDir ("gmud-coverage-weekly-{0}.csv" -f $DateTag)
    $gmudItemsOut = Join-Path $OutDir ("gmud-coverage-items-{0}.csv" -f $DateTag)
    $gmudSummaryLatest = Join-Path $OutDir "gmud-coverage-index-latest.csv"
    $gmudWeeklyLatest = Join-Path $OutDir "gmud-coverage-weekly-latest.csv"
    $gmudItemsLatest = Join-Path $OutDir "gmud-coverage-items-latest.csv"
    $downstreamLatestFiles = @(
        (Join-Path $OutDir 'w1nner-downstream-latest-data.csv'),
        (Join-Path $OutDir 's1nc-downstream-latest-data.csv'),
        (Join-Path $OutDir 'befinance-downstream-latest-data.csv'),
        (Join-Path $OutDir 'dataanalytics-downstream-latest-data.csv')
    ) | Where-Object { Test-Path $_ }
    $portfolioLatest = Join-Path $OutDir "portfolio-bt-ns-latest-data.csv"

    if ((-not $downstreamLatestFiles) -or (-not (Test-Path $portfolioLatest))) {
        Write-Warning "Pulando cobertura GMUD porque os artefatos latest de downstream/portfolio ainda não estão disponíveis."
    } else {
        Write-Host "`nCalculando cobertura GMUD x vazão Jira..." -ForegroundColor Cyan
        Write-Host "JQL CHG: $gmudChgJql"

        $gmudArgs = @(
            $gmudCoverageScript,
            '--portfolio-csv', $portfolioLatest,
            '--summary-out', $gmudSummaryOut,
            '--weekly-out', $gmudWeeklyOut,
            '--items-out', $gmudItemsOut,
            '--chg-jql', $gmudChgJql,
            '--env-file', $EnvFile,
            '--downstream-csv'
        ) + $downstreamLatestFiles

        & python @gmudArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Falha no calculo de cobertura GMUD. O restante do pipeline seguirá sem bloquear."
        } else {
            Copy-Item -Path $gmudSummaryOut -Destination $gmudSummaryLatest -Force
            Copy-Item -Path $gmudWeeklyOut -Destination $gmudWeeklyLatest -Force
            Copy-Item -Path $gmudItemsOut -Destination $gmudItemsLatest -Force
            Write-Host "Arquivos latest atualizados: $gmudSummaryLatest | $gmudWeeklyLatest | $gmudItemsLatest" -ForegroundColor Green
            Publish-LatestArtifact -SourcePath $gmudSummaryLatest -LatestDir $latestDir
            Publish-LatestArtifact -SourcePath $gmudWeeklyLatest -LatestDir $latestDir
            Publish-LatestArtifact -SourcePath $gmudItemsLatest -LatestDir $latestDir
        }
    }
}

if ($RunCapexExport) {
    if (-not (Test-Path $capexScript)) {
        throw "Arquivo não encontrado: $capexScript"
    }

    $today = Get-Date
    $capexStart = Get-Date -Year $today.Year -Month 1 -Day 1 -Format 'yyyy-MM-dd'
    $capexEnd = Get-Date -Date $today -Format 'yyyy-MM-dd'
    $capexRawLatest = Join-Path $OutDir 'capex-raw-latest.csv'
    $capexSummaryLatest = Join-Path $OutDir 'capex-summary-latest.csv'
    $capexXlsxLatest = Join-Path $OutDir 'capex-latest.xlsx'

    Write-Host "`nExportando CAPEX real por worklog..." -ForegroundColor Cyan
    Write-Host "Janela CAPEX: $capexStart -> $capexEnd"
    Write-Host "Arquivos: $capexRawLatest | $capexSummaryLatest"

    & python $capexScript `
        --projects W1NNR S1NC BF DT BT NS `
        --date-from $capexStart `
        --date-to $capexEnd `
        --out $capexRawLatest `
        --summary-out $capexSummaryLatest `
        --xlsx-out $capexXlsxLatest `
        --env-file $EnvFile `
        --workers $Workers
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Falha na exportação CAPEX por worklog. O restante do pipeline seguirá sem bloquear."
    } else {
        Publish-LatestArtifact -SourcePath $capexRawLatest -LatestDir $latestDir
        Publish-LatestArtifact -SourcePath $capexSummaryLatest -LatestDir $latestDir
        Publish-LatestArtifact -SourcePath $capexXlsxLatest -LatestDir $latestDir
    }
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

Update-LatestUploadPackage

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
