# worklog のセットアップスクリプト（DESIGN.md 10章）。
#
# このスクリプトと同じフォルダに worklog.exe / worklogw.exe / config.toml /
# export_map.toml がある状態で実行してください（インストーラではないので
# ファイルはこのフォルダから動かしません＝「各自のPCの任意フォルダ」に
# 展開したその場所がそのままインストール先になります）。
#
# 管理者権限は不要です（デスクトップとスタートアップは現在のユーザー分のみ）。
#
# 実行方法（PowerShellで）:
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$installDir = $PSScriptRoot

function Assert-File($name) {
    $p = Join-Path $installDir $name
    if (-not (Test-Path $p)) {
        Write-Host "エラー: $name が見つかりません（$installDir）。" -ForegroundColor Red
        Write-Host "build.ps1 で作られる dist_package フォルダの中身をそのまま使ってください。"
        exit 1
    }
}

Write-Host "== 必要なファイルの確認 ==" -ForegroundColor Cyan
Assert-File "worklog.exe"
Assert-File "worklogw.exe"
Assert-File "config.toml"
Assert-File "export_map.toml"

# ---------------------------------------------------------------
# 1. デスクトップのバッチファイル（day / commit）
# ---------------------------------------------------------------
Write-Host "== デスクトップにバッチファイルを作成 ==" -ForegroundColor Cyan
$desktop = [Environment]::GetFolderPath("Desktop")

$dayBat = @"
@echo off
cd /d "$installDir"
worklog.exe day
echo.
echo このウィンドウは閉じて構いません。
pause
"@
Set-Content -Path (Join-Path $desktop "今日の記録.bat") -Value $dayBat -Encoding Default

$commitBat = @"
@echo off
cd /d "$installDir"
worklog.exe commit
echo.
echo このウィンドウは閉じて構いません。
pause
"@
Set-Content -Path (Join-Path $desktop "確定する.bat") -Value $commitBat -Encoding Default

Write-Host "  作成しました: 今日の記録.bat / 確定する.bat"

# ---------------------------------------------------------------
# 2. スタートアップ登録（watch / punch を自動起動）
# ---------------------------------------------------------------
Write-Host "== スタートアップに登録 ==" -ForegroundColor Cyan
$startup = [Environment]::GetFolderPath("Startup")
$wsh = New-Object -ComObject WScript.Shell

function New-WorklogShortcut($linkName, $args) {
    $link = Join-Path $startup $linkName
    $shortcut = $wsh.CreateShortcut($link)
    $shortcut.TargetPath = Join-Path $installDir "worklogw.exe"
    $shortcut.Arguments = $args
    $shortcut.WorkingDirectory = $installDir
    $shortcut.Description = "worklog $args"
    $shortcut.Save()
}

New-WorklogShortcut "worklog watch.lnk" "watch"
New-WorklogShortcut "worklog punch.lnk" "punch"
Write-Host "  作成しました: $startup 内に worklog watch.lnk / worklog punch.lnk"
Write-Host "  次回Windows起動時から自動的に記録が始まります。"

# ---------------------------------------------------------------
# 3. 今すぐ開始（再起動を待たなくていいように）
# ---------------------------------------------------------------
Write-Host "== 今すぐ記録を開始 ==" -ForegroundColor Cyan

function Test-AlreadyRunning($argMatch) {
    $procs = Get-CimInstance Win32_Process -Filter "Name='worklogw.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        if ($p.CommandLine -and $p.CommandLine -match $argMatch) { return $true }
    }
    return $false
}

if (Test-AlreadyRunning "watch") {
    Write-Host "  watch は既に起動しています（スキップ）"
} else {
    Start-Process -FilePath (Join-Path $installDir "worklogw.exe") -ArgumentList "watch" -WorkingDirectory $installDir
    Write-Host "  watch を起動しました"
}

if (Test-AlreadyRunning "punch") {
    Write-Host "  punch は既に起動しています（スキップ）"
} else {
    Start-Process -FilePath (Join-Path $installDir "worklogw.exe") -ArgumentList "punch" -WorkingDirectory $installDir
    Write-Host "  punch（打刻ウィンドウ）を起動しました"
}

# ---------------------------------------------------------------
Write-Host ""
Write-Host "セットアップが完了しました。" -ForegroundColor Green
Write-Host ""
if (Test-Path (Join-Path $installDir "配布時の案内.txt")) {
    Write-Host "-------------------------------------------------------------"
    Get-Content (Join-Path $installDir "配布時の案内.txt") | ForEach-Object { Write-Host $_ }
    Write-Host "-------------------------------------------------------------"
} else {
    Write-Host "★ 配布時の案内.txt を必ず読み、使う人に説明してください。"
}
Write-Host ""
Write-Host "元に戻す（記録を止める）場合は uninstall.ps1 を実行してください。"
