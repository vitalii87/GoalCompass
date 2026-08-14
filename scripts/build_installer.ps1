param(
    [string]$PythonPath = "python",
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Version = (Get-Content -Raw (Join-Path $ProjectRoot "VERSION")).Trim()
$NumericVersion = ($Version -split '-', 2)[0]

if ($Version -notmatch '^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$') {
    throw "VERSION is not a valid semantic version: $Version"
}

if (-not $IsccPath) {
    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files\Inno Setup 7\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $IsccPath = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $IsccPath -or -not (Test-Path $IsccPath)) {
    throw "Inno Setup compiler (ISCC.exe) was not found."
}

Push-Location $ProjectRoot
try {
    & $PythonPath -m pip install --disable-pip-version-check -r requirements.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

    & $PythonPath -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }

    & $PythonPath -m PyInstaller --noconfirm --clean `
        --distpath (Join-Path $ProjectRoot "dist") `
        --workpath (Join-Path $ProjectRoot "build") `
        (Join-Path $ProjectRoot "installer\GoalCompass.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

    $PackagedData = Join-Path $ProjectRoot "dist\GoalCompass\data"
    if (Test-Path $PackagedData) {
        Remove-Item -LiteralPath $PackagedData -Recurse -Force
    }

    & $IsccPath "/DAppVersion=$Version" "/DNumericVersion=$NumericVersion" `
        (Join-Path $ProjectRoot "installer\GoalCompass.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }

    $Artifact = Join-Path $ProjectRoot "artifacts\GoalCompass-Setup-$Version.exe"
    if (-not (Test-Path $Artifact)) {
        throw "Installer artifact was not created: $Artifact"
    }

    Write-Host "Installer created: $Artifact"
}
finally {
    Pop-Location
}
