#Requires -RunAsAdministrator
<#
  为 IIS 应用程序池身份授予 backend 与 Python 安装目录的读取/执行权限，
  避免 HttpPlatformHandler 启动 Python 时出现 502.3（0x80070005 拒绝访问）。

  用法（管理员 PowerShell）：
    .\ensure-iis-acls.ps1
    .\ensure-iis-acls.ps1 -AppPoolName "BlogAPIPool" -BackendRoot "D:\Sites\PythonBlog\backend" -PythonHome "C:\Python312"
#>
param(
    [string] $AppPoolName = "DefaultAppPool",
    [string] $BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string] $PythonHome = ""
)

$identity = "IIS AppPool\$AppPoolName"
if (-not (Test-Path -LiteralPath $BackendRoot)) {
    Write-Error "Backend 路径不存在: $BackendRoot"
    exit 1
}

Write-Host "Grant $identity on backend: $BackendRoot"
& icacls $BackendRoot /grant "${identity}:(OI)(CI)RX" /T | Out-Null

if ($PythonHome -and (Test-Path -LiteralPath $PythonHome)) {
    Write-Host "Grant $identity on Python: $PythonHome"
    & icacls $PythonHome /grant "${identity}:(OI)(CI)RX" /T | Out-Null
} else {
    Write-Host "未指定 -PythonHome 或路径不存在，请手动对 python.exe 所在目录执行 icacls（见 docs/后端-IIS部署说明.md §7）。"
}

Write-Host "完成。请在 IIS 中回收对应应用程序池后重试访问。"
