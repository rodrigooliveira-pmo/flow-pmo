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
    [bool]$OpenDashboard = $true,
    [string]$PythonBin = ""
)

$ErrorActionPreference = 'Stop'

function Test-PythonInvoker {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$PrefixArgs = @()
    )

    try {
        $output = & $Command @PrefixArgs -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return [pscustomobject]@{
                Command    = $Command
                PrefixArgs = $PrefixArgs
            }
        }
    }
    catch {
    }

    return $null
}

function Resolve-PythonInvoker {
    param(
        [string]$PreferredCommand = ""
    )

    $candidates = New-Object System.Collections.Generic.List[object]

    if ($PreferredCommand) {
        [void]$candidates.Add(@{
            Command    = $PreferredCommand
            PrefixArgs = @()
        })
    }

    foreach ($name in @('python', 'python3')) {
        [void]$candidates.Add(@{
            Command    = $name
            PrefixArgs = @()
        })
    }

    [void]$candidates.Add(@{
        Command    = 'py'
        PrefixArgs = @('-3')
    })

    foreach ($candidate in $candidates) {
        $resolved = Test-PythonInvoker -Command $candidate.Command -PrefixArgs $candidate.PrefixArgs
        if ($null -ne $resolved) {
            return $resolved
        }
    }

    throw "Nao foi possivel localizar um interpretador Python funcional. Use -PythonBin <caminho|comando>."
}

$python = Resolve-PythonInvoker -PreferredCommand $PythonBin
$runnerScript = Join-Path $PSScriptRoot 'run_all_projects.py'
if (-not (Test-Path $runnerScript)) {
    throw "Arquivo nao encontrado: $runnerScript"
}

$argsList = @(
    $runnerScript,
    '--out-dir', $OutDir,
    '--date-tag', $DateTag,
    '--env-file', $EnvFile,
    '--workers', $Workers
)

if ($RunDetailedChangelogExport) {
    $argsList += '--run-detailed-changelog-export'
} else {
    $argsList += '--no-run-detailed-changelog-export'
}

if ($RunPortfolioExport) { $argsList += '--run-portfolio' } else { $argsList += '--no-run-portfolio' }
if ($RunGmudCoverage) { $argsList += '--run-gmud-coverage' } else { $argsList += '--no-run-gmud-coverage' }
if ($RunCapexExport) { $argsList += '--run-capex-export' } else { $argsList += '--no-run-capex-export' }
if ($RunMetrics) { $argsList += '--run-metrics' } else { $argsList += '--no-run-metrics' }
if ($OpenDashboard) { $argsList += '--run-open-dashboard' } else { $argsList += '--no-run-open-dashboard' }

& $python.Command @($python.PrefixArgs + $argsList)
exit $LASTEXITCODE
