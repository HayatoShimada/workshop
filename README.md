# worklog

パタンナーの設計工数記録ツール。詳しい設計は [`DESIGN.md`](DESIGN.md) を参照してください。

外部ライブラリには依存しません（標準ライブラリのみ、Python 3.12+）。

## セットアップ

```powershell
python -m worklog watch   # PC操作の記録を開始（バックグラウンドで動かし続ける）
python -m worklog punch   # 打刻ウィンドウを表示
```

Windows起動時に自動実行させる場合は、上記2つのショートカットをスタートアップフォルダに置いてください。

## 日々の操作

```powershell
python -m worklog day                      # 今日のタイムラインCSVを出力してExcelで開く
python -m worklog day --date 2026-08-29    # 書き忘れた日の遡り出力
python -m worklog commit                   # 編集済みタイムラインを取り込んで確定する
python -m worklog status                   # 未確定の日を一覧表示する
python -m worklog export --month 2026-08   # 転記用CSVを出力する（月1回）
```

Excelで開いたタイムラインは、`未記録` の行だけ品番・工程を埋めて保存すれば十分です。

## 設定ファイル

- `config.toml` — 勤務時間・休憩時間・打刻ボタン構成・品番/工程の自動抽出ルール
- `export_map.toml` — 転記用CSVの列構成・エンコーディング・日付書式

どちらもコード変更なしに書き換えられます。ボタン構成は担当業務ごとに配り分けてください。

## データの置き場所

すべて `data/`（生ログ・タイムライン・転記用CSV）と `logs/`（例外ログ）の中に、実行ファイルと同じフォルダに作られます。**生ログ（`data/raw/`）は本人のPCの外に一切出しません。** 提出するのは `data/export/` のCSVのみです。詳細は DESIGN.md 5章・10章を参照してください。

## 配布時に必ず説明すること（DESIGN.md 10章）

1. 何を記録するか … PCで開いているウィンドウのタイトル、操作の有無、押した打刻
2. どこに保存されるか … 自分のPCの中だけ。生ログも打刻ログも外に出ない
3. 何が提出されるか … 品番×工程×時間 の集計値のみ。**休憩の記録は含まれない**
4. 止められること … いつでも記録を停止でき、確定前の内容は自由に編集できる
5. 使わない用途 … 勤怠管理、人事評価には使用しない

特に休憩ボタンがあることで勤怠監視と受け取られやすいため、提出データに含まれない点を必ず明示してください。導入前に上長・人事への確認も行ってください。

## テスト

```powershell
python -m unittest discover -s tests -v
```

## 配布（PyInstaller）

```powershell
pip install pyinstaller
pyinstaller --onefile --name worklog worklog/__main__.py
```

`config.toml` と `export_map.toml` を生成された exe と同じフォルダに配置してください。
