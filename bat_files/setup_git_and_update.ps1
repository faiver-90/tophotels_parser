Param(
    [string]$RepoPath = ".",
    [switch]$PersistUserPath  # если указано, добавляет Git в PATH пользователя
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Find-GitPath {
    $cmd = (Get-Command git.exe -ErrorAction SilentlyContinue)
    if ($cmd) { return Split-Path -Parent $cmd.Path }
    $candidates = @(
        "$env:ProgramFiles\Git\cmd",
        "$env:ProgramFiles\Git\bin",
        "${env:ProgramFiles(x86)}\Git\cmd",
        "${env:ProgramFiles(x86)}\Git\bin",
        "$env:LocalAppData\Programs\Git\cmd",
        "$env:LocalAppData\Programs\Git\bin"
    )
    foreach ($p in $candidates) {
        if (Test-Path (Join-Path $p "git.exe")) { return $p }
    }
    return $null
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Ensure-PathContains($dir) {
    if (-not $dir) { return }
    $parts = $env:Path.Split(';') | Where-Object { $_ -and $_.Trim() -ne "" }
    if ($parts -notcontains $dir) {
        $env:Path = "$env:Path;$dir"
        Write-Info "Temporarily added to PATH: $dir"
    }
}

function Persist-To-UserPath($dir) {
    if (-not $dir) { return }
    try {
        $userPath = [System.Environment]::GetEnvironmentVariable("Path","User")
        $items = @()
        if ($userPath) { $items = $userPath.Split(';') | Where-Object { $_ -and $_.Trim() -ne "" } }
        if ($items -notcontains $dir) {
            $newUserPath = if ($userPath) { "$userPath;$dir" } else { $dir }
            [System.Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
            Write-Ok "Appended to *User* PATH: $dir"
        }
    } catch {
        Write-Warn "Could not persist to User PATH: $($_.Exception.Message)"
    }
}

function Test-GitInstalled {
    try {
        $ver = git --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            Write-Ok "Git found: $ver"
            return $true
        }
    } catch { }
    return $false
}

function Install-GitWithWinget {
    try { winget --version >$null 2>&1 | Out-Null } catch { return $false }
    Write-Info "Trying to install Git via winget (Git.Git) silently..."
    winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) { return $true }
    Write-Warn "winget finished with exit code $LASTEXITCODE"
    return $false
}

function Download-With-Retries([string]$Url, [string]$OutFile, [int]$Retries = 3) {
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            Write-Info "Download attempt $i/$Retries via Invoke-WebRequest..."
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -Headers @{ "User-Agent" = "Mozilla/5.0" }
            if (Test-Path $OutFile) { return $true }
        } catch { Write-Warn ("IWR failed: {0}" -f $_.Exception.Message) }
        Start-Sleep -Seconds (3 * $i)
    }
    return $false
}

function Install-GitFromGithub {
    $gitUrl = "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe"
    $tmp = Join-Path $env:TEMP "Git-64-bit-latest.exe"
    if (-not (Download-With-Retries -Url $gitUrl -OutFile $tmp -Retries 3)) {
        Write-Err "Failed to download Git installer from GitHub."
        return $false
    }
    Write-Info "Running silent installer..."
    $proc = Start-Process -FilePath $tmp -ArgumentList "/VERYSILENT","/NORESTART","/SP-" -Wait -PassThru
    try { Remove-Item $tmp -Force -ErrorAction SilentlyContinue } catch {}
    if ($proc.ExitCode -ne 0) {
        Write-Err "Installer exit code: $($proc.ExitCode)"
        return $false
    }
    return $true
}

function Ensure-GitAvailable {
    if (Test-GitInstalled) { return $true }
    if (Install-GitWithWinget) {
        Refresh-Path
        $p = Find-GitPath
        if ($p) {
            Ensure-PathContains $p
            if ($PersistUserPath) { Persist-To-UserPath $p }
        }
        return (Test-GitInstalled)
    }
    if (Install-GitFromGithub) {
        Refresh-Path
        $p = Find-GitPath
        if ($p) {
            Ensure-PathContains $p
            if ($PersistUserPath) { Persist-To-UserPath $p }
        }
        return (Test-GitInstalled)
    }
    return $false
}

function Ensure-GitIdentity {
    $name  = (& git config --global user.name) 2>$null
    $email = (& git config --global user.email) 2>$null
    if (-not $name) {
        $name = Read-Host "Enter git user.name"
        if ($name) {
            git config --global user.name "$name"
            Write-Ok "Set user.name = $name"
        } else {
            Write-Err "user.name is required."
            throw "user.name not set"
        }
    }
    if (-not $email) {
        $email = Read-Host "Enter git user.email"
        if ($email) {
            git config --global user.email "$email"
            Write-Ok "Set user.email = $email"
        } else {
            Write-Err "user.email is required."
            throw "user.email not set"
        }
    }
}

function Test-IsGitRepo([string]$path) { Test-Path (Join-Path $path ".git") }

try {
    if (-not (Ensure-GitAvailable)) {
        Write-Err "Git installation failed or not available."
        throw "git not available"
    }

    Ensure-GitIdentity

    if (-not (Test-Path -Path $RepoPath)) {
        New-Item -ItemType Directory -Path $RepoPath -Force | Out-Null
    }
    $fullPath = (Get-Item -LiteralPath $RepoPath).FullName
    Write-Info "Repo path: $fullPath"

    Push-Location $fullPath
    try {
        if (-not (Test-IsGitRepo $fullPath)) {
            Write-Warn "No .git found at $fullPath"
            Write-Info "Initializing new git repo..."
            git init
            git branch -M main 2>$null | Out-Null
            git remote add origin https://github.com/faiver-90/tophotels_parser.git
            git reset --hard HEAD
            git clean -fd
            git pull origin main
            Write-Ok "Repo initialized and linked to HTTPS remote."
        } else {
            Write-Ok "Git repo already initialized."
        }

        # Обновляем проект из origin/main
        Write-Info "Pulling latest changes from origin/main..."
        git pull origin main
        if ($LASTEXITCODE -ne 0) {
            Write-Err "git pull failed. Возможно, нужны креды (PAT/логин+пароль)."
            throw "git pull failed"
        }
        Write-Ok "Repo updated from origin/main."
    }
    finally { Pop-Location }

    Write-Ok "Done."
    exit 0
}
catch {
    Write-Err $_
    exit 1
}
