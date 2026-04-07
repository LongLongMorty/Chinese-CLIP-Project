# ============================================================
#  Chinese-CLIP 商品检索系统 - 一键启动脚本
# ============================================================

$ROOT        = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = $ROOT
$FRONTEND_DIR = Join-Path $ROOT "frontend\image-search"

# PyTorch conda 环境下的 Python 可执行文件（直接调用，不走 conda activate，避免 GBK 编码报错）
$PYTHON = "D:\Anaconda3\envs\PyTorch\python.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Chinese-CLIP 商品检索系统 启动中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 启动后端 ----------
Write-Host "[1/2] 启动 Flask 后端 (http://localhost:5000) ..." -ForegroundColor Yellow

$backendCmd = @"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$env:PYTHONIOENCODING = 'utf-8'
`$env:PYTHONUTF8 = '1'
`$env:KMP_DUPLICATE_LIB_OK = 'TRUE'
Write-Host '=== Flask 后端 ===' -ForegroundColor Green
Set-Location '$BACKEND_DIR'
& '$PYTHON' app.py
"@

Start-Process powershell -ArgumentList "-NoProfile", "-NoExit", "-Command", $backendCmd -WindowStyle Normal

Start-Sleep -Seconds 2

# ---------- 启动前端 ----------
Write-Host "[2/2] 启动 Vue 前端 (http://localhost:5173) ..." -ForegroundColor Yellow

$frontendCmd = @"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host '=== Vue 前端 ===' -ForegroundColor Green
Set-Location '$FRONTEND_DIR'
npm run dev
"@

Start-Process powershell -ArgumentList "-NoProfile", "-NoExit", "-Command", $frontendCmd -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  启动完成！" -ForegroundColor Green
Write-Host "  后端地址: http://localhost:5000" -ForegroundColor Green
Write-Host "  前端地址: http://localhost:5173" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "关闭对应的 PowerShell 窗口即可停止服务。" -ForegroundColor Gray
