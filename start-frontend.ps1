<#
    前端开发服务启动入口。在项目根目录运行 .\start-frontend.ps1。
    优先使用系统 pnpm；未安装时兼容本机已配置的运行时。
#>
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendPath = Join-Path $projectRoot "frontend"
$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpmCommand) {
    # 可通过 CODEX_NODE_RUNTIME 指定本地运行时目录。
    $runtime = if ($env:CODEX_NODE_RUNTIME) { $env:CODEX_NODE_RUNTIME } else {
        Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
    }
    $nodePath = Join-Path $runtime "node\bin"
    $fallbackPath = Join-Path $runtime "bin\fallback"
    $candidate = Join-Path $fallbackPath "pnpm.cmd"
    if (-not (Test-Path $candidate)) {
        throw "未找到 pnpm。请安装 Node.js 22 与 pnpm 10.17.1，并将其加入 PATH。"
    }
    $env:Path = "$fallbackPath;$nodePath;$env:Path"
    $pnpmCommand = $candidate
}
if (-not (Test-Path $frontendPath)) { throw "前端目录不存在：$frontendPath" }
Push-Location $frontendPath
try { & $pnpmCommand dev } finally { Pop-Location }
