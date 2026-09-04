# worklog を止めるスクリプト（DESIGN.md 10章「止められること」）。
#
# 実行すると:
#   - watch / punch のプロセスを終了する
#   - スタートアップ登録（自動起動）を削除する
#   - デスクトップのバッチファイルを削除する
#
# data フォルダ（記録そのもの）は削除しません。記録を完全に消したい
# 場合は、このスクリプト実行後に手動で data フォルダを削除してください。

$ErrorActionPreference = "Continue"
$installDir = $PSScriptRoot

Write-Host "== worklog watch / punch を終了 ==" -ForegroundColor Cyan
$procs = Get-CimInstance Win32_Process -Filter "Name='worklogw.exe'" -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    Write-Host "  停止: PID $($p.ProcessId)  ($($p.CommandLine))"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "== スタートアップ登録を削除 ==" -ForegroundColor Cyan
$startup = [Environment]::GetFolderPath("Startup")
foreach ($name in @("worklog watch.lnk", "worklog punch.lnk")) {
    $link = Join-Path $startup $name
    if (Test-Path $link) {
        Remove-Item $link -Force
        Write-Host "  削除: $link"
    }
}

Write-Host "== デスクトップのバッチファイルを削除 ==" -ForegroundColor Cyan
$desktop = [Environment]::GetFolderPath("Desktop")
foreach ($name in @("今日の記録.bat", "確定する.bat")) {
    $bat = Join-Path $desktop $name
    if (Test-Path $bat) {
        Remove-Item $bat -Force
        Write-Host "  削除: $bat"
    }
}

Write-Host ""
Write-Host "停止しました。記録データ（$installDir\data）はそのまま残っています。" -ForegroundColor Green
Write-Host "完全に削除したい場合は、data フォルダを手動で削除してください。"
