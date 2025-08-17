Param(
    [string]$RepoPath = ".",
    [switch]$PersistUserPath  # if set, append Git path to *User* PATH (no admin required)
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Find-GitPath {
    # Try PATH first
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
    # Rebuild current process PATH from Machine+User to pick up changes made by installers
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Ensure-PathContains($dir) {
    if (-not $dir) { return }
    # Add to current session PATH if missing
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
    # --silent ensures no UI (UAC consent may still appear if needed)
    winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) { return $true }
    Write-Warn "winget finished with exit code $LASTEXITCODE"
    return $false
}

function Download-With-Retries([string]$Url, [string]$OutFile, [int]$Retries = 3) {
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
    } catch {
        try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
    }
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            Write-Info "Download attempt $i/$Retries via Invoke-WebRequest..."
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -Headers @{ "User-Agent" = "Mozilla/5.0" }
            if (Test-Path $OutFile) { return $true }
        } catch {
            Write-Warn ("IWR failed: {0}" -f $_.Exception.Message)
        }
        Start-Sleep -Seconds (3 * $i)
    }
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            Write-Info "Download attempt $i/$Retries via BITS..."
            Start-BitsTransfer -Source $Url -Destination $OutFile -ErrorAction Stop
            if (Test-Path $OutFile) { return $true }
        } catch {
            Write-Warn ("BITS failed: {0}" -f $_.Exception.Message)
        }
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
    Write-Info "Running silent installer (/VERYSILENT /NORESTART /SP-)..."
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

    # Try winget
    if (Install-GitWithWinget) {
        Refresh-Path
        $p = Find-GitPath
        if ($p) {
            Ensure-PathContains $p
            if ($PersistUserPath) { Persist-To-UserPath $p }
        }
        return (Test-GitInstalled)
    }

    # Try GitHub installer
    Write-Warn "winget failed or unavailable. Falling back to GitHub installer."
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
        Write-Warn "git user.name is not set."
        $name = Read-Host "Enter git user.name"
        if ($name) {
            git config --global user.name "$name"
            Write-Ok "Set user.name = $name"
        } else {
            Write-Err "user.name is required."
            throw "user.name not set"
        }
    } else { Write-Ok "user.name = $name" }

    if (-not $email) {
        Write-Warn "git user.email is not set."
        $email = Read-Host "Enter git user.email"
        if ($email) {
            git config --global user.email "$email"
            Write-Ok "Set user.email = $email"
        } else {
            Write-Err "user.email is required."
            throw "user.email not set"
        }
    } else { Write-Ok "user.email = $email" }
}

function Test-IsGitRepo([string]$path) { Test-Path (Join-Path $path ".git") }

function Get-CurrentBranch {
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $branch) { return $null }
    return $branch
}

function Test-WorkingTreeClean {
    git update-index -q --refresh | Out-Null
    git diff --quiet --ignore-submodules HEAD -- 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Get-BehindAhead($branch) {
    $counts = (git rev-list --left-right --count "origin/$branch...HEAD" 2>$null).Trim()
    if (-not $counts) { return [pscustomobject]@{ Behind = 0; Ahead = 0 } }
    $parts = $counts -split "\s+"
    if ($parts.Count -ge 2) { return [pscustomobject]@{ Behind = [int]$parts[0]; Ahead = [int]$parts[1] } }
    return [pscustomobject]@{ Behind = 0; Ahead = 0 }
}

try {
    if (-not (Ensure-GitAvailable)) {
        Write-Err "Git installation failed or git still not available in PATH."
        throw "git not available"
    }

    Ensure-GitIdentity

    $fullPath = Resolve-Path -Path $RepoPath
    Write-Info "Repo path: $fullPath"
    if (-not (Test-IsGitRepo $fullPath)) { Write-Err "Not a git repo (no .git)"; throw "Not a git repo" }

    Push-Location $fullPath
    try {
        Write-Info "git fetch --all --prune"
        git fetch --all --prune
        if ($LASTEXITCODE -ne 0) {
            $remote = (git remote get-url origin) 2>$null
            Write-Err "git fetch failed. origin=$remote"
            if ($remote -match '^git@' -or $remote -match '^ssh://') {
                Write-Info "It looks like SSH. Ensure ssh-agent is running, your key is added (ssh-add), and the public key is registered in your Git host account."
                Write-Info "Test with: ssh -T git@github.com"
            } elseif ($remote -match '^https://') {
                Write-Info "It looks like HTTPS. Configure Git Credential Manager and use a Personal Access Token (PAT) on first prompt."
                Write-Info "Run: git config --global credential.helper manager"
                Write-Info "Then run: git ls-remote origin and enter PAT as password."
            } else {
                Write-Info "Unknown remote scheme. Verify 'git remote -v'."
            }
            throw "git fetch failed"
        }

        $branch = Get-CurrentBranch
        if (-not $branch -or $branch -eq "HEAD") { Write-Err "Detached HEAD or unknown branch."; throw "Unknown branch" }
        Write-Ok ("Current branch: {0}" -f $branch)

        $stat = Get-BehindAhead -branch $branch
        Write-Info ("Remote status vs origin/{0}: behind={1}, ahead={2}" -f $branch, $stat.Behind, $stat.Ahead)

        if ($stat.Behind -gt 0) {
            if (Test-WorkingTreeClean) {
                Write-Info "Working tree clean. Pull with rebase..."
                git pull --rebase origin $branch
                if ($LASTEXITCODE -ne 0) { throw "git pull --rebase failed" }
                Write-Ok "Updated successfully."
            } else {
                Write-Warn "Local changes detected. Auto-stash, pull --rebase, then try to apply stash."
                git stash push -u -m ("auto-stash before update {0}" -f (Get-Date -Format s))
                if ($LASTEXITCODE -ne 0) { throw "git stash failed" }

                git pull --rebase origin $branch
                if ($LASTEXITCODE -ne 0) { Write-Err "pull failed; your changes remain in stash."; throw "pull failed" }

                git stash pop
                if ($LASTEXITCODE -ne 0) { Write-Warn "Conflicts applying stash. Resolve manually." }
                else { Write-Ok "Updated and re-applied local changes." }
            }
        } else {
            Write-Ok ("Already up to date with origin/{0}." -f $branch)
        }
    } finally { Pop-Location }

    Write-Ok "Done."
    exit 0
}
catch {
    Write-Err $_
    exit 1
}
