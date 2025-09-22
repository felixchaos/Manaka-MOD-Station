param(
    [string]$NewRepoName = "Manaka-MOD-Station",
    [string]$NewRepoDescription = "塞雷卡mod管理器",
    [string]$RemoteName = "origin",
    [switch]$ForceDelete = $false
)

# This script uses GitHub CLI (gh). Make sure you have gh installed and authenticated: gh auth login
# It will:
# 1) create a local backup zip under tools/backups
# 2) delete the remote repository (owner/repo) - requires you to be the owner
# 3) create a new repository with the new name
# 4) set remote and force-push current branch

set -e

$pwd = Get-Location
$repoRoot = $pwd.Path
$backupsDir = Join-Path $repoRoot "tools\backups"
New-Item -ItemType Directory -Force -Path $backupsDir | Out-Null

# create a zip backup of the repo
$timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$zipPath = Join-Path $backupsDir "repo-backup-$timestamp.zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($repoRoot, $zipPath)
Write-Host "Backup created at $zipPath"

# determine current remote repository (assumes 'origin' exists)
$originUrl = git remote get-url $RemoteName
if (-not $originUrl) {
    Write-Host "Remote $RemoteName not found. Aborting." -ForegroundColor Red
    exit 1
}

# extract owner and repo slug from origin url
# supports HTTPS and SSH
if ($originUrl -match "[:/]([^/]+)/([^/]+)(?:\.git)?$") {
    $owner = $Matches[1]
    $repo = $Matches[2]
} else {
    Write-Host "Cannot parse origin URL: $originUrl" -ForegroundColor Red
    exit 1
}

Write-Host "Current remote: $owner/$repo"

# delete remote repo
if ($ForceDelete) {
    gh repo delete "$owner/$repo" --confirm
    Write-Host "Deleted remote repository $owner/$repo"
} else {
    $confirm = Read-Host "Are you sure you want to DELETE remote repository $owner/$repo and recreate a new one named $NewRepoName? Type YES to confirm"
    if ($confirm -ne "YES") {
        Write-Host "Aborted by user." -ForegroundColor Yellow
        exit 1
    }
    gh repo delete "$owner/$repo" --confirm
}

# create new repo under same owner
$createCmd = "gh repo create $owner/$NewRepoName --public --description `"$NewRepoDescription`" --confirm"
Write-Host "Creating new repository: $owner/$NewRepoName"
Invoke-Expression $createCmd

# Update remote url
$newOriginUrl = "https://github.com/$owner/$NewRepoName.git"
git remote set-url $RemoteName $newOriginUrl

# Force-push current branch to new remote
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "Pushing branch $currentBranch to $owner/$NewRepoName (force)"
git push $RemoteName $currentBranch --force

Write-Host "Done. New repository https://github.com/$owner/$NewRepoName created and current branch pushed."
Write-Host "Please reconfigure repository settings, secrets, releases, and collaborators as needed."
