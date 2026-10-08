param()

$ErrorActionPreference = 'Stop'

Push-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
try {
    $venvPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw 'Virtual environment not found. Run .\run.ps1 -CheckOnly first.'
    }

    $steps = @(
        @{ Name = 'Security policy'; Args = @('scripts/check_security_requirements.py', '--stage', 'build') },
        @{ Name = 'Secret scan'; Args = @('scripts/check_secrets.py') },
        @{ Name = 'Ruff'; Args = @('-m', 'ruff', 'check', '.', '--exclude', '.venv,.test-tmp-*', '--select', 'E9,F') },
        @{ Name = 'Bandit'; Args = @('-m', 'bandit', '-q', '-r', 'agent.py', 'app.py', 'config.py', 'backend', 'database', 'services', 'security', 'tools', 'workflows', 'evals', 'scripts', '-x', 'tests,backend/tests') },
        @{ Name = 'Dependency audit'; Args = @('-m', 'pip_audit', '--requirement', 'requirements.lock.txt', '--no-deps', '--disable-pip', '--progress-spinner', 'off') },
        @{ Name = 'Deterministic tests'; Args = @('-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp', '.venv\pytest-security-gate') },
        @{ Name = 'Short load check'; Args = @('scripts/run_load_check.py', '--duration-seconds', '2', '--fake-provider-delay-seconds', '0.2') }
    )

    foreach ($step in $steps) {
        Write-Host ("Running {0}..." -f $step.Name)
        & $venvPython @($step.Args)
        if ($LASTEXITCODE -ne 0) {
            throw ("{0} failed." -f $step.Name)
        }
    }

    Write-Host 'BUILD security gate passed. GitHub Actions will also verify the Linux Docker build.'
}
finally {
    Pop-Location
}
