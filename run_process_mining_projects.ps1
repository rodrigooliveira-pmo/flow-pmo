param(
    [string]$OutDir = "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados",
    [string]$LatestDir = $(if ($env:FLOW_PMO_LATEST_DIR) { $env:FLOW_PMO_LATEST_DIR } else { "C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest" }),
    [string]$DateTag = $(Get-Date -Format 'yyyyMMdd'),
    [string]$EnvFile = $(Join-Path $PSScriptRoot 'jira_env.txt'),
    [int]$Workers = 8,
    [string]$JqlExtra = "",
    [switch]$RunDashboardModel,
    [string]$PythonBin = "",
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

function Show-Usage {
    @"
Uso: .\run_process_mining_projects.ps1 [opcoes]

Opcoes:
  -OutDir PATH             Diretorio de saida para downstream e Bitbucket
  -LatestDir PATH          Diretorio latest central
  -DateTag YYYYMMDD        Tag de data para os arquivos
  -EnvFile PATH            Arquivo com variaveis JIRA_* e BB_*
  -Workers N               Numero de workers para exportacao Jira
  -JqlExtra JQL            Filtro JQL adicional repassado ao export Jira
  -RunDashboardModel       Roda dash_board_metricas.py no final para atualizar PowerBI_Model_latest.xlsx
  -PythonBin CMD_OR_PATH   Comando/caminho preferido do interpretador Python
  -Help                    Mostra esta ajuda

Observacoes:
  - Sem -RunDashboardModel, o script atualiza downstream, process mining e Bitbucket.
  - Com -RunDashboardModel, o script tambem atualiza o modelo consolidado usado pelo dashboard_full.
"@
}

if ($Help) {
    Show-Usage
    exit 0
}

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

function Test-PythonInvoker {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$PrefixArgs = @(),
        [string]$DisplayName = $Command
    )

    try {
        $output = & $Command @PrefixArgs -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            $resolvedExe = ($output | Select-Object -Last 1).ToString().Trim()
            if ($resolvedExe) {
                return [pscustomobject]@{
                    Command     = $Command
                    PrefixArgs  = $PrefixArgs
                    DisplayName = $DisplayName
                    Executable  = $resolvedExe
                }
            }
        }
    }
    catch {
    }

    return $null
}

function Get-PythonCandidatePaths {
    $paths = New-Object System.Collections.Generic.List[string]

    $roots = @()
    if ($env:LOCALAPPDATA) {
        $roots += (Join-Path $env:LOCALAPPDATA 'Programs\Python')
    }
    $roots += 'C:\Python311'
    $roots += 'C:\Python310'
    $roots += 'C:\Python39'

    foreach ($root in $roots) {
        if (-not (Test-Path $root)) {
            continue
        }

        if (Test-Path (Join-Path $root 'python.exe')) {
            [void]$paths.Add((Join-Path $root 'python.exe'))
        }

        Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $candidate = Join-Path $_.FullName 'python.exe'
            if (Test-Path $candidate) {
                [void]$paths.Add($candidate)
            }
        }
    }

    return $paths | Select-Object -Unique
}

function Resolve-PythonInvoker {
    param(
        [string]$PreferredCommand = ""
    )

    $candidates = New-Object System.Collections.Generic.List[object]

    if ($PreferredCommand) {
        [void]$candidates.Add(@{
            Command     = $PreferredCommand
            PrefixArgs  = @()
            DisplayName = "preferido: $PreferredCommand"
        })
    }

    foreach ($name in @('python', 'python3')) {
        [void]$candidates.Add(@{
            Command     = $name
            PrefixArgs  = @()
            DisplayName = $name
        })
    }

    [void]$candidates.Add(@{
        Command     = 'py'
        PrefixArgs  = @('-3')
        DisplayName = 'py -3'
    })

    foreach ($path in Get-PythonCandidatePaths) {
        [void]$candidates.Add(@{
            Command     = $path
            PrefixArgs  = @()
            DisplayName = $path
        })
    }

    foreach ($candidate in $candidates) {
        $resolved = Test-PythonInvoker -Command $candidate.Command -PrefixArgs $candidate.PrefixArgs -DisplayName $candidate.DisplayName
        if ($null -ne $resolved) {
            return $resolved
        }
    }

    throw "Nao foi possivel localizar um interpretador Python funcional. Use -PythonBin <caminho|comando>."
}

function Invoke-PythonScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    & $script:PythonInvoker.Command @($script:PythonInvoker.PrefixArgs + @($ScriptPath) + $Arguments)
    return $LASTEXITCODE
}

Import-EnvFile -Path $EnvFile -OverrideExisting $true

if (-not $env:JIRA_BASE_URL -or -not $env:JIRA_EMAIL -or -not $env:JIRA_API_TOKEN) {
    throw "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN (ou preencha o arquivo $EnvFile) antes de executar."
}

$scriptPath = Join-Path $PSScriptRoot 'jira_to_pipeline_csv.py'
$processMiningScript = Join-Path $PSScriptRoot 'process_mining_jira.py'
$bitbucketScript = Join-Path $PSScriptRoot 'bitbucket_export.py'
$dashboardMetricsScript = Join-Path $PSScriptRoot 'dash_board_metricas.py'
$processMiningOutDir = Join-Path $PSScriptRoot 'artifacts\process_mining'
$processMiningFailures = New-Object System.Collections.Generic.List[string]
$bitbucketFailures = New-Object System.Collections.Generic.List[string]

if (-not (Test-Path $scriptPath)) {
    throw "Arquivo não encontrado: $scriptPath"
}
if (-not (Test-Path $processMiningScript)) {
    throw "Arquivo não encontrado: $processMiningScript"
}
if (-not (Test-Path $bitbucketScript)) {
    throw "Arquivo não encontrado: $bitbucketScript"
}
if ($RunDashboardModel -and -not (Test-Path $dashboardMetricsScript)) {
    throw "Arquivo não encontrado: $dashboardMetricsScript"
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}
if (-not (Test-Path $LatestDir)) {
    New-Item -ItemType Directory -Path $LatestDir -Force | Out-Null
}
if (-not (Test-Path $processMiningOutDir)) {
    New-Item -ItemType Directory -Path $processMiningOutDir -Force | Out-Null
}

$script:PythonInvoker = Resolve-PythonInvoker -PreferredCommand $PythonBin
Write-Host "Python selecionado: $($script:PythonInvoker.DisplayName) -> $($script:PythonInvoker.Executable)" -ForegroundColor DarkCyan

$projects = @(
    @{ Key = 'W1NNR'; FilePrefix = 'w1nner-downstream'; ProcessMiningPrefix = 'w1nner-process-mining'; BitbucketProject = 'W1NNR' },
    @{ Key = 'S1NC'; FilePrefix = 's1nc-downstream'; ProcessMiningPrefix = 's1nc-process-mining'; BitbucketProject = 'S1NC' },
    @{ Key = 'BF'; FilePrefix = 'befinance-downstream'; ProcessMiningPrefix = 'befinance-process-mining'; BitbucketProject = 'BF' },
    @{ Key = 'DT'; FilePrefix = 'dataanalytics-downstream'; ProcessMiningPrefix = 'dataanalytics-process-mining'; BitbucketProject = 'DT' }
)

Write-Host "Iniciando exportação dedicada de process mining..." -ForegroundColor Cyan
Write-Host "Base URL: $($env:JIRA_BASE_URL)"
Write-Host "Saída changelog: $OutDir"
Write-Host "Saída process mining: $processMiningOutDir"
Write-Host "Saída latest: $LatestDir"
Write-Host "Data: $DateTag"
if ($JqlExtra) {
    Write-Host "Filtro JQL adicional: $JqlExtra"
}
if ($RunDashboardModel) {
    Write-Host "Refresh do PowerBI_Model_latest.xlsx: habilitado" -ForegroundColor Cyan
}

$originalJiraStatusMap = $env:JIRA_STATUS_MAP
if ($env:JIRA_STATUS_MAP) {
    Write-Host "Ignorando JIRA_STATUS_MAP global durante exportação downstream para process mining (fluxo por projeto habilitado)." -ForegroundColor DarkYellow
}
Remove-Item -Path Env:JIRA_STATUS_MAP -ErrorAction SilentlyContinue
$env:JIRA_IGNORE_STATUS_MAP = '1'

foreach ($p in $projects) {
    $outFile = Join-Path $OutDir ("{0}-{1}-data.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogOut = Join-Path $OutDir ("{0}-{1}-data_detailed_changelog.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogLatest = Join-Path $OutDir ("{0}-latest-data_detailed_changelog.csv" -f $p.FilePrefix)

    Write-Host "`nProjeto: $($p.Key)" -ForegroundColor Yellow
    Write-Host "Changelog detalhado: $detailedChangelogOut"

    $jiraArgs = @(
        '--projects', $p.Key,
        '--out', $outFile,
        '--env-file', $EnvFile,
        '--workers', $Workers,
        '--detailed-changelog-out', $detailedChangelogOut
    )
    if ($JqlExtra) {
        $jiraArgs += @('--jql-extra', $JqlExtra)
    }

    $jiraExit = Invoke-PythonScript -ScriptPath $scriptPath -Arguments $jiraArgs
    if ($jiraExit -ne 0) {
        throw "Falha na exportação downstream detalhada do projeto $($p.Key)."
    }

    if (Test-Path $detailedChangelogOut) {
        Copy-Item -Path $detailedChangelogOut -Destination $detailedChangelogLatest -Force
        Write-Host "Arquivo latest atualizado: $detailedChangelogLatest" -ForegroundColor Green
        Publish-LatestArtifact -SourcePath $detailedChangelogLatest -LatestDir $LatestDir
    }

    Write-Host "Gerando process mining para $($p.Key)..." -ForegroundColor Cyan
    $pmExit = Invoke-PythonScript -ScriptPath $processMiningScript -Arguments @(
        '--input', $detailedChangelogOut,
        '--out-dir', $processMiningOutDir,
        '--project', $p.Key,
        '--prefix', $p.ProcessMiningPrefix
    )
    if ($pmExit -eq 0) {
        Sync-LatestArtifactsFromOutDir -SourceDir $processMiningOutDir -LatestDir $LatestDir
    }
    else {
        $status = $pmExit
        Write-Warning "Process mining falhou para $($p.Key) (exit $status)."
        [void]$processMiningFailures.Add("$($p.Key):exit-$status")
    }

    Write-Host "Exportando Bitbucket para $($p.BitbucketProject)..." -ForegroundColor Cyan
    $bbExit = Invoke-PythonScript -ScriptPath $bitbucketScript -Arguments @(
        '--project', $p.BitbucketProject,
        '--out-dir', $OutDir
    )
    if ($bbExit -eq 0) {
        foreach ($suffix in @('commits', 'pullrequests', 'pipelines')) {
            $bitbucketFile = Join-Path $OutDir ("{0}_{1}.csv" -f $p.FilePrefix.Replace('-downstream', ''), $suffix)
            if (Test-Path $bitbucketFile) {
                Publish-LatestArtifact -SourcePath $bitbucketFile -LatestDir $LatestDir
            }
        }
    }
    else {
        $status = $bbExit
        Write-Warning "Falha na extração Bitbucket do projeto $($p.BitbucketProject) (exit $status)."
        [void]$bitbucketFailures.Add("$($p.BitbucketProject):exit-$status")
    }
}

if ($null -ne $originalJiraStatusMap -and $originalJiraStatusMap -ne '') {
    $env:JIRA_STATUS_MAP = $originalJiraStatusMap
}
Remove-Item -Path Env:JIRA_IGNORE_STATUS_MAP -ErrorAction SilentlyContinue

if ($RunDashboardModel) {
    Write-Host "`nAtualizando modelo consolidado para o dashboard_full..." -ForegroundColor Cyan
    $originalFlowPmoDataDir = $env:FLOW_PMO_DATA_DIR
    $originalDataFolder = $env:DATA_FOLDER
    $originalFlowPmoLatestDir = $env:FLOW_PMO_LATEST_DIR

    try {
        $env:FLOW_PMO_DATA_DIR = $OutDir
        $env:DATA_FOLDER = $OutDir
        $env:FLOW_PMO_LATEST_DIR = $LatestDir

        $dashboardExit = Invoke-PythonScript -ScriptPath $dashboardMetricsScript
        if ($dashboardExit -ne 0) {
            throw "Falha ao atualizar PowerBI_Model_latest.xlsx (exit $dashboardExit)."
        }
    }
    finally {
        if ($null -ne $originalFlowPmoDataDir) {
            $env:FLOW_PMO_DATA_DIR = $originalFlowPmoDataDir
        }
        else {
            Remove-Item -Path Env:FLOW_PMO_DATA_DIR -ErrorAction SilentlyContinue
        }

        if ($null -ne $originalDataFolder) {
            $env:DATA_FOLDER = $originalDataFolder
        }
        else {
            Remove-Item -Path Env:DATA_FOLDER -ErrorAction SilentlyContinue
        }

        if ($null -ne $originalFlowPmoLatestDir) {
            $env:FLOW_PMO_LATEST_DIR = $originalFlowPmoLatestDir
        }
        else {
            Remove-Item -Path Env:FLOW_PMO_LATEST_DIR -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "`nExportação dedicada de process mining concluída." -ForegroundColor Green
if ($processMiningFailures.Count -gt 0) {
    Write-Warning ("Avisos Process Mining: " + ($processMiningFailures -join ", "))
}
if ($bitbucketFailures.Count -gt 0) {
    Write-Warning ("Avisos Bitbucket: " + ($bitbucketFailures -join ", "))
}
