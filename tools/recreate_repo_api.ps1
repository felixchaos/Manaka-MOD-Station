<#
PowerShell script to delete and recreate a GitHub repository using the REST API.
Requires:
- A GitHub Personal Access Token (PAT) with 'repo' scope stored in env var GITHUB_TOKEN.
- This script will NOT run automatically; run it yourself after verifying the backup created by the other script.
#>
param(
    [string]$Owner,
    [string]$Repo,
    [string]$NewRepoName = "Manaka-MOD-Station",
    [string]$NewRepoDescription = "塞雷卡mod管理器",
    [switch]$ForceDelete
)

if (-not $env:GITHUB_TOKEN) { Write-Error "Please set GITHUB_TOKEN env var with a PAT that has 'repo' scope."; exit 1 }

$headers = @{ Authorization = "token $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github+json' }

function ApiDeleteRepo($owner, $repo) {
    $url = "https://api.github.com/repos/$owner/$repo"
    Invoke-RestMethod -Uri $url -Method Delete -Headers $headers -ErrorAction Stop
}

function ApiCreateRepo($owner, $name, $description) {
    $url = "https://api.github.com/user/repos"
    $body = @{ name = $name; description = $description; private = $false } | ConvertTo-Json
    Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $body -ErrorAction Stop
}

# backup
$backupsDir = Join-Path (Get-Location).Path 'tools\backups'
New-Item -ItemType Directory -Force -Path $backupsDir | Out-Null
$timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$zip = Join-Path $backupsDir "repo-backup-$timestamp.zip"
Compress-Archive -Path . -DestinationPath $zip -Force
Write-Host "Backup created at $zip"

if ($ForceDelete) {
    ApiDeleteRepo -owner $Owner -repo $Repo
    Write-Host "Deleted remote repo $Owner/$Repo"
} else {
    $confirm = Read-Host "Type YES to DELETE remote repo $Owner/$Repo"
    if ($confirm -ne 'YES') { Write-Host 'Aborted'; exit 1 }
    ApiDeleteRepo -owner $Owner -repo $Repo
}

ApiCreateRepo -owner $Owner -name $NewRepoName -description $NewRepoDescription
Write-Host "Created new repo $NewRepoName. Please set collaborators and settings as needed."

Write-Host "Update local remote and push manually with:
    git remote set-url origin https://github.com/$Owner/$NewRepoName.git
    git push origin --all --force
"