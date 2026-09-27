param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

Push-Location -LiteralPath $PSScriptRoot
try {
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host 'Creating Python virtual environment...'
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment. Install Python 3.11+ and retry.' }
    }

    Write-Host 'Installing project dependencies...'
    & $venvPython -m pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

    if (-not (Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
        Write-Host 'Created .env. Add OPENAI_API_KEY there to enable AI chat.'
    }

    Write-Host 'Initializing demo data...'
    & $venvPython -m database.seed
    if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }

    Write-Host 'Running offline tests...'
    $pytestTemp = Join-Path $PSScriptRoot ('.venv\pytest-' + [guid]::NewGuid().ToString('N'))
    try {
        & $venvPython -m pytest -q -p no:cacheprovider --basetemp $pytestTemp
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; app startup stopped.' }
    }
    finally {
        if (Test-Path -LiteralPath $pytestTemp) {
            try {
                Remove-Item -LiteralPath $pytestTemp -Recurse -Force -ErrorAction Stop
            }
            catch {
                Write-Warning "Could not remove test temp directory: $pytestTemp"
            }
        }
    }

    if ($CheckOnly) {
        Write-Host 'Setup and checks passed. Run .\run.ps1 to start BizPilot AI.'
        return
    }

    Write-Host 'Starting BizPilot AI...'
    & $venvPython -m streamlit run app.py --server.headless true --browser.gatherUsageStats false
    if ($LASTEXITCODE -ne 0) { throw 'Streamlit exited with an error.' }
}
finally {
    Pop-Location
}
