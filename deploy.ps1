$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$deployScript = Join-Path $scriptDir 'deploy'

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCmd) {
    & py $deployScript @args
    exit $LASTEXITCODE
}

& python $deployScript @args
exit $LASTEXITCODE
