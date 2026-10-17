<#
    research-collab 安装脚本（Windows / PowerShell）

    用法：
        .\install.ps1                 安装到 ~/.agents/skills/research-collab
        .\install.ps1 -Codex          再让 Codex 可见（在 ~/.codex/skills 建目录联接）
        .\install.ps1 -Force          覆盖已安装版本

    说明：
        DSH 读取 ~/.agents/skills；Codex 读取 ~/.codex/skills。
        用目录联接（junction）指向同一份文件，改一处两边同时生效。
#>

[CmdletBinding()]
param(
    [switch]$Codex,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$src = $PSScriptRoot
$name = 'research-collab'
$agentsHome = if ($env:DSH_AGENTS_HOME) { $env:DSH_AGENTS_HOME } else { Join-Path $HOME '.agents' }
$dest = Join-Path $agentsHome "skills\$name"

if (-not (Test-Path (Join-Path $src 'SKILL.md'))) {
    Write-Host "找不到 SKILL.md；请在仓库根目录运行本脚本。" -ForegroundColor Red
    exit 2
}

if ((Test-Path $dest) -and -not $Force) {
    Write-Host "已安装：$dest" -ForegroundColor Yellow
    Write-Host "要覆盖请加 -Force" -ForegroundColor Yellow
    exit 1
}

if ((Test-Path $dest) -and $Force) {
    Write-Host "移除旧版本：$dest"
    Remove-Item $dest -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($item in @('SKILL.md', 'README.md', 'LICENSE', 'references', 'scripts', 'templates', 'examples', 'integrations')) {
    $path = Join-Path $src $item
    if (Test-Path $path) {
        Copy-Item $path -Destination $dest -Recurse -Force
    }
}

Write-Host "已安装到 $dest" -ForegroundColor Green

if ($Codex) {
    $codexRoot = Join-Path $HOME '.codex\skills'
    $link = Join-Path $codexRoot $name
    New-Item -ItemType Directory -Force -Path $codexRoot | Out-Null
    if (Test-Path $link) {
        Write-Host "已存在，跳过：$link（如需重建先手动删除）" -ForegroundColor Yellow
    }
    else {
        try {
            New-Item -ItemType Junction -Path $link -Target $dest | Out-Null
            Write-Host "已链接给 Codex：$link" -ForegroundColor Green
        }
        catch {
            Copy-Item $dest $link -Recurse -Force
            Write-Host "目录联接不可用，已复制给 Codex：$link" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "验证安装："
Write-Host "  python `"$dest\scripts\init_workspace.py`" `"<项目目录>`" --title `"题目`""

exit 0
