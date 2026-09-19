$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$CARGO_ABOUT_VERSION="0.8.2"
$outputFile=$args[0] ? $args[0] : "$(Get-Location)/assets/licenses.md"
$templateFile="script/licenses/template.md.hbs"

New-Item -Path "$outputFile" -ItemType File -Value "" -Force

@(
    "# ###### THEME LICENSES ######\n"
    Get-Content assets/themes/LICENSES
    "\n# ###### ICON LICENSES ######\n"
    Get-Content assets/icons/LICENSES
    "\n# ###### CODE LICENSES ######\n"
) | Add-Content -Path $outputFile

$cargoBin = if ($env:CARGO_HOME) { "$env:CARGO_HOME\bin" } else { "$env:USERPROFILE\.cargo\bin" }
if (Test-Path $cargoBin) {
    if ($env:Path -notlike "*$cargoBin*") {
        $env:Path = "$cargoBin;$env:Path"
    }
}

$needsInstall = $false
try {
    $versionOutput = & cargo about --version 2>$null
    if (-not ($versionOutput -match "cargo-about $CARGO_ABOUT_VERSION")) {
        # Wrong version counts as missing: silently generating with a stale
        # cargo-about is what the pin is supposed to prevent.
        $needsInstall = $true
    } else {
        Write-Host "cargo-about@$CARGO_ABOUT_VERSION is already installed"
    }
} catch {
    $needsInstall = $true
}

if ($needsInstall) {
    Write-Host "Installing cargo-about@$CARGO_ABOUT_VERSION..."
    cargo install "cargo-about@$CARGO_ABOUT_VERSION"
}

Write-Host "Generating cargo licenses"

$failFlag = $env:ALLOW_MISSING_LICENSES ? "--fail" : ""
$aboutExe = if (Test-Path "$cargoBin\cargo-about.exe") {
    "$cargoBin\cargo-about.exe"
} elseif (Get-Command "cargo-about.exe" -ErrorAction SilentlyContinue) {
    "cargo-about.exe"
} else {
    $null
}

if ($aboutExe) {
    $aboutArgs = @('generate', $failFlag, '-c', 'script/licenses/zed-licenses.toml', $templateFile, '-o', $outputFile) | Where-Object { $_ }
    & $aboutExe @aboutArgs
} else {
    $args = @('about', 'generate', $failFlag, '-c', 'script/licenses/zed-licenses.toml', $templateFile, '-o', $outputFile) | Where-Object { $_ }
    cargo @args
}

Write-Host "Applying replacements"
$replacements = @{
    '&quot;' = '"'
    '&#x27;' = "'"
    '&#x3D;' = '='
    '&#x60;' = '`'
    '&lt;'   = '<'
    '&gt;'   = '>'
}
$content = Get-Content $outputFile
foreach ($find in $replacements.keys) {
    $content = $content -replace $find, $replacements[$find]
}
$content | Set-Content $outputFile

Write-Host "generate-licenses completed. See $outputFile"
