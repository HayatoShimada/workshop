# worklog を配布用にビルドするスクリプト（DESIGN.md 10章）。
#
# 2つのexeを作ります。
#   worklog.exe   … コンソール表示あり。day / commit / export / status 用
#   worklogw.exe  … コンソール表示なし。watch / punch 用
#                    （スタートアップ起動時に黒いウィンドウを出さないため）
#
# 実行後、dist_package/ に配布用一式（exe2つ・config.toml・export_map.toml・
# install.ps1・uninstall.ps1）がまとまります。このフォルダごとzipして配れば
# パタンナー側は展開して install.ps1 を実行するだけで使えます。

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "== PyInstaller の確認 ==" -ForegroundColor Cyan
$pyinstaller = python -m pip show pyinstaller 2>$null
if (-not $pyinstaller) {
    Write-Host "PyInstaller が見つかりません。インストールします..."
    python -m pip install pyinstaller
}

Write-Host "== 既存のビルド成果物を削除 ==" -ForegroundColor Cyan
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$root\build", "$root\dist", "$root\dist_package"

Write-Host "== worklog.exe をビルド（コンソールあり: day/commit/export/status用） ==" -ForegroundColor Cyan
python -m PyInstaller --onefile --name worklog --distpath "$root\dist" --workpath "$root\build" --specpath "$root\build" "$root\worklog\__main__.py"

Write-Host "== worklogw.exe をビルド（コンソールなし: watch/punch用） ==" -ForegroundColor Cyan
python -m PyInstaller --onefile --windowed --name worklogw --distpath "$root\dist" --workpath "$root\build" --specpath "$root\build" "$root\worklog\__main__.py"

Write-Host "== 配布用フォルダを組み立て (dist_package/) ==" -ForegroundColor Cyan
$pkg = "$root\dist_package"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null
Copy-Item "$root\dist\worklog.exe"     "$pkg\worklog.exe"
Copy-Item "$root\dist\worklogw.exe"    "$pkg\worklogw.exe"
Copy-Item "$root\config.toml"          "$pkg\config.toml"
Copy-Item "$root\export_map.toml"      "$pkg\export_map.toml"
Copy-Item "$root\install.ps1"          "$pkg\install.ps1"
Copy-Item "$root\uninstall.ps1"        "$pkg\uninstall.ps1"
Copy-Item "$root\配布時の案内.txt"      "$pkg\配布時の案内.txt"

Write-Host ""
Write-Host "完成: $pkg" -ForegroundColor Green
Write-Host "このフォルダをそのまま（またはzipにして）配ってください。"
Write-Host "パタンナー側は展開後、install.ps1 を実行すれば使い始められます。"
