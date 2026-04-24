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

function Format-CommandForDisplay {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @()
    )

    $parts = @($Command) + $Arguments
    $display = foreach ($part in $parts) {
        $text = [string]$part
        if ($text -match '\s' -or $text -match '"') {
            '"' + ($text -replace '"', '\"') + '"'
        }
        else {
            $text
        }
    }
    return ($display -join ' ')
}

function Invoke-PythonScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @(),
        [string]$Label = ""
    )

    $fullArgs = @($script:PythonInvoker.PrefixArgs + @($ScriptPath) + $Arguments)
    $display = Format-CommandForDisplay -Command $script:PythonInvoker.DisplayName -Arguments $fullArgs
    if ($Label) {
        Write-Host "Executando [$Label]: $display" -ForegroundColor DarkGray
    }
    else {
        Write-Host "Executando: $display" -ForegroundColor DarkGray
    }

    try {
        & $script:PythonInvoker.Command @fullArgs 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                Write-Host $_.ToString() -ForegroundColor Red
            }
            else {
                Write-Host $_
            }
        }
        $exitCode = $LASTEXITCODE
        return [int]$exitCode
    }
    catch {
        $labelText = if ($Label) { " [$Label]" } else { "" }
        throw "Falha ao iniciar comando Python${labelText}: $display`n$($_.Exception.Message)"
    }
}

function Invoke-PythonScriptWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @(),
        [string]$Label = "",
        [int]$MaxAttempts = 3,
        [int[]]$BackoffSeconds = @(2, 4, 8)
    )

    $lastExit = -1
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $lastExit = Invoke-PythonScript -ScriptPath $ScriptPath -Arguments $Arguments -Label $Label
        }
        catch {
            if ($attempt -ge $MaxAttempts) { throw }
            $delay = if (($attempt - 1) -lt $BackoffSeconds.Count) { $BackoffSeconds[$attempt - 1] } else { $BackoffSeconds[-1] }
            Write-Warning "Tentativa $attempt/$MaxAttempts falhou ao iniciar [$Label]. Nova tentativa em ${delay}s. Erro: $($_.Exception.Message)"
            Start-Sleep -Seconds $delay
            continue
        }

        if ($lastExit -eq 0) { return 0 }

        if ($attempt -lt $MaxAttempts) {
            $delay = if (($attempt - 1) -lt $BackoffSeconds.Count) { $BackoffSeconds[$attempt - 1] } else { $BackoffSeconds[-1] }
            Write-Warning "Tentativa $attempt/$MaxAttempts retornou exit $lastExit [$Label]. Nova tentativa em ${delay}s."
            Start-Sleep -Seconds $delay
        }
    }

    return $lastExit
}

function Reset-BitbucketEnvScope {
    Remove-Item -Path Env:BB_REPOS              -ErrorAction SilentlyContinue
    Remove-Item -Path Env:BB_REPO               -ErrorAction SilentlyContinue
    Remove-Item -Path Env:BB_COMMIT_DEPTH        -ErrorAction SilentlyContinue
    Remove-Item -Path Env:BB_MIN_REQUEST_INTERVAL_MS -ErrorAction SilentlyContinue
}

function Test-OutputFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$MinBytes = 512
    )

    if (-not (Test-Path $Path)) { return $false }
    return (Get-Item $Path).Length -ge $MinBytes
}

Import-EnvFile -Path $EnvFile -OverrideExisting $true

if (-not $env:JIRA_BASE_URL -or -not $env:JIRA_EMAIL -or -not $env:JIRA_API_TOKEN) {
    throw "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN (ou preencha o arquivo $EnvFile) antes de executar."
}

$scriptPath = Join-Path $PSScriptRoot 'jira_to_pipeline_csv.py'
$processMiningScript = Join-Path $PSScriptRoot 'process_mining_jira.py'
$bitbucketScript = Join-Path $PSScriptRoot 'bitbucket_export.py'
$dashboardMetricsScript = Join-Path $PSScriptRoot 'dash_board_metricas.py'
$copyLatestUploadScript = Join-Path $PSScriptRoot 'copy_latest_upload.py'
$processMiningOutDir = Join-Path $PSScriptRoot 'artifacts\process_mining'
$jiraBitbucketCommitDepth = if ($env:FLOW_PMO_JIRA_BB_COMMIT_DEPTH) { $env:FLOW_PMO_JIRA_BB_COMMIT_DEPTH } else { '250' }
$jiraBitbucketMinIntervalMs = if ($env:FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS) { $env:FLOW_PMO_JIRA_BB_MIN_REQUEST_INTERVAL_MS } else { '750' }
$bitbucketExportWorkers = if ($env:FLOW_PMO_BITBUCKET_EXPORT_WORKERS) { [int]$env:FLOW_PMO_BITBUCKET_EXPORT_WORKERS } else { 1 }
$bitbucketExportMinIntervalMs = if ($env:FLOW_PMO_BITBUCKET_EXPORT_MIN_REQUEST_INTERVAL_MS) { $env:FLOW_PMO_BITBUCKET_EXPORT_MIN_REQUEST_INTERVAL_MS } else { '900' }
$dtBoardJql = 'project in (10290) AND issuetype in (10254, 10255,10258, 10257,Bug,Ad-hoc) ORDER BY Rank ASC'
$jiraFailures = New-Object System.Collections.Generic.List[string]
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
if (-not (Test-Path $copyLatestUploadScript)) {
    throw "Arquivo não encontrado: $copyLatestUploadScript"
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

$projects = @(
    @{ Key = 'W1NNR'; FilePrefix = 'w1nner-downstream'; ProcessMiningPrefix = 'w1nner-process-mining'; BitbucketProject = 'W1NNR'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'W1NNR') },
    @{ Key = 'S1NC'; FilePrefix = 's1nc-downstream'; ProcessMiningPrefix = 's1nc-process-mining'; BitbucketProject = 'S1NC'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'S1NC') },
    @{ Key = 'BF'; FilePrefix = 'befinance-downstream'; ProcessMiningPrefix = 'befinance-process-mining'; BitbucketProject = 'BF'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'BF') },
    @{ Key = 'DT'; FilePrefix = 'dataanalytics-downstream'; ProcessMiningPrefix = 'dataanalytics-process-mining'; BitbucketProject = 'DT'; BitbucketRepos = (Get-ProjectBitbucketRepos -ProjectKey 'DT'); Jql = $dtBoardJql }
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
# Jobs usam env isolado — captura/restore de BB vars no processo pai não é mais necessária.
# JIRA_STATUS_MAP já removido acima; JIRA_IGNORE_STATUS_MAP definido acima.

$pythonExe_  = $script:PythonInvoker.Executable
$prefixArgs_ = $script:PythonInvoker.PrefixArgs
$tempDir_    = [System.IO.Path]::GetTempPath()

$jiraEnv = @{
    JIRA_BASE_URL          = [string]$env:JIRA_BASE_URL
    JIRA_EMAIL             = [string]$env:JIRA_EMAIL
    JIRA_API_TOKEN         = [string]$env:JIRA_API_TOKEN
    JIRA_IGNORE_STATUS_MAP = '1'
}

$projectMeta   = @{}
$jiraJobs      = [ordered]@{}
$jiraExitFiles = @{}
$bbJobs        = [ordered]@{}
$bbExitFiles   = @{}

Write-Host "`nIniciando jobs em paralelo (Jira + Bitbucket por projeto)..." -ForegroundColor Cyan

foreach ($p in $projects) {
    $outFile                 = Join-Path $OutDir ("{0}-{1}-data.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogOut    = Join-Path $OutDir ("{0}-{1}-data_detailed_changelog.csv" -f $p.FilePrefix, $DateTag)
    $detailedChangelogLatest = Join-Path $OutDir ("{0}-latest-data_detailed_changelog.csv" -f $p.FilePrefix)

    $projectMeta[$p.Key] = @{
        Project                 = $p
        OutFile                 = $outFile
        DetailedChangelogOut    = $detailedChangelogOut
        DetailedChangelogLatest = $detailedChangelogLatest
    }

    # Jira args
    $jiraArgsList = [System.Collections.Generic.List[string]]@(
        '--projects', $p.Key,
        '--out', $outFile,
        '--env-file', $EnvFile,
        '--workers', [string]$Workers,
        '--detailed-changelog-out', $detailedChangelogOut,
        '--skip-devexecutor-bitbucket'
    )
    if ($p.Jql) {
        $jiraArgsList.AddRange([string[]]@('--jql', $p.Jql))
        Write-Host "[$($p.Key)] JQL dedicada: $($p.Jql)" -ForegroundColor DarkCyan
        if ($JqlExtra) { Write-Warning "JqlExtra ignorado para $($p.Key) (JQL dedicada ativa)." }
    } elseif ($JqlExtra) {
        $jiraArgsList.AddRange([string[]]@('--jql-extra', $JqlExtra))
    }
    $jiraArgsFinal = $jiraArgsList.ToArray()

    $jiraExitFile = Join-Path $tempDir_ ("jira_exit_$($p.Key)_$DateTag.tmp")
    $jiraExitFiles[$p.Key] = $jiraExitFile
    $jiraLabel = "jira_to_pipeline_csv $($p.Key)"
    $scriptPath_ = $scriptPath

    Write-Host "Iniciando job Jira: $($p.Key)" -ForegroundColor DarkGray

    $jiraJobs[$p.Key] = Start-Job -ScriptBlock {
        param($exe, $prefixArgs, $scriptPath, $jiraArgs, $envHash, $label, $maxAttempts, $backoff, $exitFile)
        foreach ($k in $envHash.Keys) { [System.Environment]::SetEnvironmentVariable($k, $envHash[$k]) }
        $lastExit = -1
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            $fullArgs = $prefixArgs + @($scriptPath) + $jiraArgs
            Write-Output "[$label] Tentativa $attempt/$maxAttempts"
            & $exe @fullArgs 2>&1 | ForEach-Object { Write-Output $_ }
            $lastExit = $LASTEXITCODE
            if ($lastExit -eq 0) { break }
            if ($attempt -lt $maxAttempts) {
                $delay = if (($attempt - 1) -lt $backoff.Count) { $backoff[$attempt - 1] } else { $backoff[-1] }
                Write-Output "[$label] Exit $lastExit — nova tentativa em ${delay}s."
                Start-Sleep -Seconds $delay
            }
        }
        [string]$lastExit | Out-File -FilePath $exitFile -NoNewline -Encoding ascii
    } -ArgumentList $pythonExe_, $prefixArgs_, $scriptPath_, $jiraArgsFinal, $jiraEnv, $jiraLabel, 3, @(2, 4, 8), $jiraExitFile

    # Bitbucket job — independente do Jira, inicia imediatamente
    if ($p.BitbucketRepos) {
        $bbEnvLocal = @{
            BB_REPOS                   = $p.BitbucketRepos
            BB_REPO                    = ($p.BitbucketRepos -split ',')[0]
            BB_COMMIT_DEPTH            = $jiraBitbucketCommitDepth
            BB_MIN_REQUEST_INTERVAL_MS = $jiraBitbucketMinIntervalMs
        }
        foreach ($k in $jiraEnv.Keys) { $bbEnvLocal[$k] = $jiraEnv[$k] }

        $bbArgsFinal = @(
            '--project', $p.BitbucketProject,
            '--out-dir', $OutDir,
            '--workers', [string]$bitbucketExportWorkers,
            '--min-request-interval-ms', $bitbucketExportMinIntervalMs
        )
        $bbExitFile  = Join-Path $tempDir_ ("bb_exit_$($p.Key)_$DateTag.tmp")
        $bbExitFiles[$p.Key] = $bbExitFile
        $bbLabel     = "bitbucket_export $($p.BitbucketProject)"
        $bbScript_   = $bitbucketScript

        Write-Host "Iniciando job Bitbucket: $($p.BitbucketProject)" -ForegroundColor DarkGray

        $bbJobs[$p.Key] = Start-Job -ScriptBlock {
            param($exe, $prefixArgs, $scriptPath, $bbArgs, $envHash, $label, $maxAttempts, $backoff, $exitFile)
            foreach ($k in $envHash.Keys) { [System.Environment]::SetEnvironmentVariable($k, $envHash[$k]) }
            $lastExit = -1
            for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
                $fullArgs = $prefixArgs + @($scriptPath) + $bbArgs
                Write-Output "[$label] Tentativa $attempt/$maxAttempts"
                & $exe @fullArgs 2>&1 | ForEach-Object { Write-Output $_ }
                $lastExit = $LASTEXITCODE
                if ($lastExit -eq 0) { break }
                if ($attempt -lt $maxAttempts) {
                    $delay = if (($attempt - 1) -lt $backoff.Count) { $backoff[$attempt - 1] } else { $backoff[-1] }
                    Write-Output "[$label] Exit $lastExit — nova tentativa em ${delay}s."
                    Start-Sleep -Seconds $delay
                }
            }
            [string]$lastExit | Out-File -FilePath $exitFile -NoNewline -Encoding ascii
        } -ArgumentList $pythonExe_, $prefixArgs_, $bbScript_, $bbArgsFinal, $bbEnvLocal, $bbLabel, 3, @(2, 4, 8), $bbExitFile
    } else {
        Write-Warning "Projeto $($p.Key) sem repos Bitbucket configurados. Pulando."
        [void]$bitbucketFailures.Add("$($p.Key):no-repos-configured")
        $bbJobs[$p.Key] = $null
    }
}

# --- Fan-in: monitora Jira jobs; dispara Process Mining por projeto assim que Jira conclui ---
$pmJobs      = [ordered]@{}
$pmExitFiles = @{}
$pendingJiraKeys = [System.Collections.Generic.HashSet[string]]($jiraJobs.Keys)

Write-Host "`nMonitorando Jira. Process Mining inicia por projeto assim que Jira conclui..." -ForegroundColor Cyan

while ($pendingJiraKeys.Count -gt 0) {
    $runningJiraJobs = @(
        $jiraJobs.GetEnumerator() |
            Where-Object { $pendingJiraKeys.Contains($_.Key) } |
            ForEach-Object { $_.Value }
    )
    $doneJob = Wait-Job -Job $runningJiraJobs -Any -Timeout 30
    if ($null -eq $doneJob) { continue }

    foreach ($job in @($doneJob)) {
        $key = ($jiraJobs.GetEnumerator() | Where-Object { $_.Value.Id -eq $job.Id }).Key
        [void]$pendingJiraKeys.Remove($key)

        Write-Host "`n--- Output Jira: $key ---" -ForegroundColor Yellow
        Receive-Job $job | ForEach-Object { Write-Host $_ }
        Remove-Job $job -Force -ErrorAction SilentlyContinue

        $jiraExit = if (Test-Path $jiraExitFiles[$key]) {
            [int](Get-Content $jiraExitFiles[$key] -Raw -ErrorAction SilentlyContinue)
        } else { -1 }
        Remove-Item $jiraExitFiles[$key] -ErrorAction SilentlyContinue

        $meta = $projectMeta[$key]

        if ($jiraExit -ne 0) {
            Write-Warning "Job Jira falhou para $key (exit $jiraExit)."
            [void]$jiraFailures.Add("$key`:exit-$jiraExit")
        } elseif (Test-OutputFile -Path $meta.DetailedChangelogOut) {
            Copy-Item -Path $meta.DetailedChangelogOut -Destination $meta.DetailedChangelogLatest -Force
            Write-Host "Arquivo latest atualizado: $($meta.DetailedChangelogLatest)" -ForegroundColor Green
            Publish-LatestArtifact -SourcePath $meta.DetailedChangelogLatest -LatestDir $LatestDir

            Write-Host "Iniciando job Process Mining: $key" -ForegroundColor Cyan
            $pmExitFile  = Join-Path $tempDir_ ("pm_exit_$key`_$DateTag.tmp")
            $pmExitFiles[$key] = $pmExitFile
            $p_          = $meta.Project
            $pmArgsFinal = @('--input', $meta.DetailedChangelogOut, '--out-dir', $processMiningOutDir, '--project', $key, '--prefix', $p_.ProcessMiningPrefix)
            $pmScript_   = $processMiningScript
            $pmLabel     = "process_mining_jira $key"

            $pmJobs[$key] = Start-Job -ScriptBlock {
                param($exe, $prefixArgs, $scriptPath, $pmArgs, $envHash, $label, $exitFile)
                foreach ($k in $envHash.Keys) { [System.Environment]::SetEnvironmentVariable($k, $envHash[$k]) }
                $fullArgs = $prefixArgs + @($scriptPath) + $pmArgs
                Write-Output "[$label] Iniciando"
                & $exe @fullArgs 2>&1 | ForEach-Object { Write-Output $_ }
                $lastExit = $LASTEXITCODE
                [string]$lastExit | Out-File -FilePath $exitFile -NoNewline -Encoding ascii
            } -ArgumentList $pythonExe_, $prefixArgs_, $pmScript_, $pmArgsFinal, $jiraEnv, $pmLabel, $pmExitFile
        } else {
            Write-Warning "Changelog detalhado ausente ou vazio para $key; process mining será pulado."
            [void]$processMiningFailures.Add("$key`:skipped-empty-detailed-changelog")
        }
    }
}

# --- Aguarda Process Mining jobs ---
if ($pmJobs.Count -gt 0) {
    Write-Host "`nAguardando jobs Process Mining..." -ForegroundColor Cyan
    $nonNullPm = @($pmJobs.Values | Where-Object { $null -ne $_ })
    if ($nonNullPm.Count -gt 0) { Wait-Job -Job $nonNullPm | Out-Null }

    foreach ($kvp in $pmJobs.GetEnumerator()) {
        $key = $kvp.Key
        Write-Host "`n--- Output Process Mining: $key ---" -ForegroundColor Yellow
        Receive-Job $kvp.Value | ForEach-Object { Write-Host $_ }
        Remove-Job $kvp.Value -Force -ErrorAction SilentlyContinue

        $pmExit = if (Test-Path $pmExitFiles[$key]) {
            [int](Get-Content $pmExitFiles[$key] -Raw -ErrorAction SilentlyContinue)
        } else { -1 }
        Remove-Item $pmExitFiles[$key] -ErrorAction SilentlyContinue

        if ($pmExit -eq 0) {
            Sync-LatestArtifactsFromOutDir -SourceDir $processMiningOutDir -LatestDir $LatestDir
        } else {
            Write-Warning "Process Mining falhou para $key (exit $pmExit)."
            [void]$processMiningFailures.Add("$key`:exit-$pmExit")
        }
    }
}

# --- Aguarda Bitbucket jobs (muitos já concluídos em paralelo com Jira) ---
Write-Host "`nAguardando jobs Bitbucket..." -ForegroundColor Cyan
$nonNullBb = @($bbJobs.Values | Where-Object { $null -ne $_ })
if ($nonNullBb.Count -gt 0) { Wait-Job -Job $nonNullBb | Out-Null }

foreach ($kvp in $bbJobs.GetEnumerator()) {
    $key = $kvp.Key
    if ($null -eq $kvp.Value) { continue }

    Write-Host "`n--- Output Bitbucket: $key ---" -ForegroundColor Yellow
    Receive-Job $kvp.Value | ForEach-Object { Write-Host $_ }
    Remove-Job $kvp.Value -Force -ErrorAction SilentlyContinue

    $bbExit = if (Test-Path $bbExitFiles[$key]) {
        [int](Get-Content $bbExitFiles[$key] -Raw -ErrorAction SilentlyContinue)
    } else { -1 }
    Remove-Item $bbExitFiles[$key] -ErrorAction SilentlyContinue

    $p_ = $projectMeta[$key].Project
    if ($bbExit -eq 0) {
        foreach ($suffix in @('commits', 'pullrequests', 'pipelines')) {
            $bitbucketFile = Join-Path $OutDir ("{0}_{1}.csv" -f $p_.FilePrefix.Replace('-downstream', ''), $suffix)
            if (Test-Path $bitbucketFile) {
                Publish-LatestArtifact -SourcePath $bitbucketFile -LatestDir $LatestDir
            }
        }
    } else {
        Write-Warning "Falha na extração Bitbucket para $($p_.BitbucketProject) (exit $bbExit)."
        [void]$bitbucketFailures.Add("$($p_.BitbucketProject):exit-$bbExit")
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

        $dashboardExit = Invoke-PythonScript -ScriptPath $dashboardMetricsScript -Label "dash_board_metricas"
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

& $script:PythonInvoker.Executable $copyLatestUploadScript --source-dir $LatestDir --dest-dir (Join-Path $LatestDir 'latest-upload') --clean-dest
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao atualizar a pasta latest-upload."
}

$awsS3Bucket = if ($env:AWS_S3_BUCKET) { $env:AWS_S3_BUCKET } else { 'w1-flow-pmo-dashboards' }
$awsRegion   = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { 'us-east-1' }
$uploadDir   = Join-Path $LatestDir 'latest-upload'
if (Get-Command aws -ErrorAction SilentlyContinue) {
    Write-Host "`nIniciando upload para S3 (bucket: $awsS3Bucket, regiao: $awsRegion)..." -ForegroundColor Cyan
    & aws s3 cp "$uploadDir/" "s3://$awsS3Bucket/" --recursive --region $awsRegion
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Upload S3 falhou (exit $LASTEXITCODE)."
    } else {
        Write-Host "Upload S3 concluido." -ForegroundColor Green
    }
} else {
    Write-Warning "aws CLI nao encontrado. Upload S3 pulado."
}

Write-Host "`nExportação dedicada de process mining concluída." -ForegroundColor Green
if ($jiraFailures.Count -gt 0) {
    Write-Warning ("Avisos Jira/Downstream: " + ($jiraFailures -join ", "))
}
if ($processMiningFailures.Count -gt 0) {
    Write-Warning ("Avisos Process Mining: " + ($processMiningFailures -join ", "))
}
if ($bitbucketFailures.Count -gt 0) {
    Write-Warning ("Avisos Bitbucket: " + ($bitbucketFailures -join ", "))
}
