# AGENTS.md

このリポジトリは、東京工科大学の学外シラバスを取得し、Cloudflare Pages で静的 JSON API として配信するためのものです。エージェントは、既存 API の互換性と大量の生成済み JSON を壊さないことを最優先にしてください。

## リポジトリ構成

- `generate.py`: GitHub Actions で使う本番系の生成スクリプトです。講義コード取得と講義データ取得を分けて実行します。
- `main.py`: ローカル開発用スクリプトです。`compose.yaml` の Selenium Grid に接続します。CI では使われていません。
- `src/get_lecture_code.py`: 学外シラバス検索画面を Selenium で操作し、学部ごとの時間割コード一覧を取得します。
- `src/get_timetable.py`: 個別シラバス HTML を取得・解析し、API レスポンス用 dict を作ります。
- `output/lecture_codes.json`: 現在年度の学部ごとの時間割コード一覧です。従来互換用に維持されています。
- `output/lecture_codes_by_year.json`: 年度別の時間割コード一覧です。この archive repo では 2024-2027 年度だけを対象にします。
- `docs/api/v1/archive/{year}/all/*.json`: 2024-2027 年度の年度指定 API 用の生成済み講義 JSON です。過去データは削除しません。
- `docs/api/v1/archive/{year}/search-index/{department}.json`: 2024-2027 年度の年度別アーカイブの学部別サーチインデックスです。
- `scripts/import_archive_year.py`: 現行 API から確定済み年度の詳細 JSON、search-index、講義コード一覧を検証してコピーします。
- `.github/workflows/build.yaml`: 毎年3月31日に現行 API から2年前の大学年度をコピーするワークフローです。

## セットアップ

GitHub Actions は Python `3.11.9` を使っています。ローカルでも同じ系統を使うのが無難です。

```sh
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --upgrade get-chrome-driver
pip install -r requirements.txt
```

`get-chrome-driver` は `generate.py` で import されますが、`requirements.txt` には入っておらず、workflow 側で個別にインストールされています。

## 主要コマンド

対象アーカイブ年度の講義コード一覧を再取得します。`--year` を省略した場合は 2024-2027 年度を対象にしますが、現在年度に該当する年度はスキップします。

```sh
python generate.py --type=lecture_codes
```

特定学部の講義データを再取得します。`--year` を省略した場合は 2024-2027 年度を対象にしますが、現在年度に該当する年度はスキップします。

```sh
python generate.py --type=lecture_data --department=CS
```

特定年度だけを明示して再取得できます。2024-2027 年度以外、または現在年度はスキップします。

```sh
python generate.py --type=lecture_codes --year=2024
python generate.py --type=lecture_data --department=CS --year=2024
```

学部別サーチインデックスを再生成します。曜日・時限・`regularOrIntensive`・教員名・開講時期・対象学年・科目区分の絞り込み用キーは、サーチインデックスに含まれます。

```sh
python generate.py --type=indexes
python generate.py --type=indexes --year=2024
```

`--department` に指定できる値は `generate.py` の `DEPARTMENT` を確認してください。`HSH3` と `HSH4` は `output/lecture_codes.json` で `null` になることがあり、その場合は講義データ生成をスキップします。

ローカル Selenium Grid を使って `main.py` を動かす場合は、先にコンテナを起動します。

```sh
docker compose up -d
python main.py
```

`main.py` は `output/lecture_codes.json` が存在すると講義コード取得をスキップします。通常の更新や CI と同じ挙動を確認したい場合は `generate.py` を使ってください。

## 開発時の注意

- 生成済み JSON は大量にあります。スクレイピングや整形ロジックを変更した場合でも、必要な学部・必要な講義だけを確認してから広範囲の再生成を行ってください。
- API レスポンスのキーは利用者向けの契約です。特に `courceDetails` はスペルミスに見えますが、既存 API のキーなので、互換性の意図なしに `courseDetails` へ変更しないでください。
- この archive repo の対象年度は `generate.py` の `ARCHIVE_START_YEAR` から `ARCHIVE_END_YEAR` までです。現在年度に該当する年度は取得しません。年度別の詳細データは `docs/api/v1/archive/{year}/all` に書き込みます。学部別詳細 JSON は廃止済みです。
- 過去データは削除しない方針です。生成ロジックを変える場合も、明示的な依頼なしに `docs/api/v1/archive` 配下の古い年度を消さないでください。
- 定期アーカイブでは学外シラバスを再取得せず、`Rinia777/TUT-Timetable-API` の `docs/api/v1/archive/{year}` をコピーします。対象は実行時点の大学年度から2年前です。
- コピー前後で全 JSON の構文、search-index の `count`、対象年度の講義コード一覧を検証します。検証に失敗したデータをコミットしないでください。
- 現行年度専用の `search-index/manifest.json` は年度アーカイブへ追加しません。
- `search-index` 配下のファイルは講義 JSON から作り直せる派生データです。索引生成では古い `search-index` ディレクトリだけを削除して再生成しますが、講義 JSON 本体は削除しません。
- `output/lecture_codes_by_year.json` は講義データ生成の主な入力です。講義コード取得ロジックを変更したときは、このファイルと従来互換用の `output/lecture_codes.json` の差分を確認してください。
- `src/get_timetable.py` は年度指定がない場合、現在年を基準にシラバス URL を作り、1 月から 3 月は前年度を取得します。年度境界の変更ではこの挙動に注意してください。
- 現行の検索画面は iframe ではなく、年度は `input#nendo`、所属は `select#jikanwariShozokuCd`、詳細リンクは `viewSyllabus('/syllabus/{year}/{department}/{department}_{lectureCode}_ja_JP.html')` 形式です。旧 URL 形式への後方互換は `get_timetable.py` に残しています。
- `get_lecture_code.py` では `BT` の select value に特殊文字を含む値を使っています。学部コード周りを整理するときに削らないでください。
- `X1` は教養科目として必須、というコメントがあります。学部リストを変更するときは `README.md`、`generate.py`、`main.py`、workflow matrix を揃えてください。

## テストと検証

このリポジトリには現時点で自動テスト、formatter、linter の設定がありません。変更後は最低限、以下を実施してください。

```sh
python -m py_compile generate.py main.py src/get_lecture_code.py src/get_timetable.py
python generate.py --type=lecture_data --department=GF
```

スクレイピングを伴うコマンドは外部サイトと Chrome/ChromeDriver に依存します。ネットワークやブラウザ環境が使えない場合は、実行できなかったことを明記し、コードレベルの構文確認だけでも行ってください。

## データ更新フロー

定期更新は `.github/workflows/build.yaml` で管理されています。

1. 毎年3月31日 JST 3:40 に現行 API リポジトリを読み取り専用で checkout します。
2. 当日の大学年度から2年前（3月31日の暦年から3年前）を対象年度とします。
3. 対象年度が 2024-2027 の範囲なら、詳細 JSON、search-index、年度別講義コードを検証してコピーします。範囲外なら安全にスキップします。
4. コピー後の検証に成功し、差分がある場合だけコミットします。手動実行では対象年度を指定できます。

workflow や学部リストを変える場合は、README の API 仕様に書かれた学部一覧も合わせて更新してください。
