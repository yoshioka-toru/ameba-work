# API レスポンス比較ツール

このディレクトリには、API v1.0とv2.0のレスポンスを比較するためのツールが含まれています。

## 概要

1. `create_diff_api.sh`: access.logからcalendars APIのパスを抽出し、`target_path`ファイルを作成します
2. `diff_api_response.py`: `target_path`ファイルに記載されたパスに対して、v1.0とv2.0のAPIレスポンスを比較します

## 必要な環境

### create_diff_api.sh
- bash
- grep
- jq (JSONパーサー)

### diff_api_response.py
- Python 3.x
- curlコマンド

## 使い方

### 1. target_pathファイルの作成

`access.log`からcalendars APIのパスを抽出して`target_path`ファイルを作成します。

```bash
./create_diff_api.sh
```

**処理内容:**
- `access.log`から「calendars」を含む行を抽出
- URIから`/v1.0/`や`/v2.0/`のプレフィックスを削除
- クエリパラメータから`ym`と`language`を抽出
- パスとクエリパラメータを結合して`target_path`ファイルに出力

**出力例:**
```
public/blog/10062932273/calendars?ym=202510
public/blog/10000430222/calendars?ym=202510&language=0
```

### 2. APIレスポンスの比較

`target_path`ファイルに記載されたパスに対して、v1.0とv2.0のAPIレスポンスを比較します。

```bash
python3 diff_api_response.py
```

**処理内容:**
- `target_path`ファイルを読み込み
- 各パスに対して以下を実行:
  1. v1.0のAPIにGETリクエストを送信
  2. v2.0のAPIにGETリクエストを送信
  3. HTTPステータスコードとレスポンスボディを比較
  4. 不一致があれば詳細を出力

**出力例:**
```
比較開始: 100個のパスを処理します

[1/100] パス: public/blog/10062932273/calendars?ym=202510 ... 一致
[2/100] パス: public/blog/10000430222/calendars?ym=202510 ... 不一致
  v1.0: https://stg-blog-internal-api.tama.local/v1.0/public/blog/10000430222/calendars?ym=202510
  v2.0: https://stg-blog-internal-api.tama.local/v2.0/public/blog/10000430222/calendars?ym=202510
  v1.0レスポンス:
  {
    "data": {...}
  }
  
  v2.0レスポンス:
  {
    "data": {...}
  }
```

## ファイル構成

```
202511_diff_api_response/
├── README.md                 # このファイル
├── create_diff_api.sh        # target_pathファイル作成スクリプト
├── diff_api_response.py      # APIレスポンス比較スクリプト
└── target_path               # APIパス一覧（create_diff_api.shの出力、diff_api_response.pyの入力）
```

## 各スクリプトの詳細

### create_diff_api.sh

**機能:**
- `access.log`から「calendars」を含む行を抽出
- JSON形式のログをパースして、URIとクエリパラメータを抽出
- パスとクエリパラメータを整形して`target_path`ファイルに出力

**設定:**
- `LOG_FILE`: 入力ログファイル名（デフォルト: `access.log`）
- `OUTPUT_FILE`: 出力ファイル名（デフォルト: `target_path`）

**抽出ルール:**
- URIから`/v1.0/`や`/v2.0/`のプレフィックスを削除
- クエリパラメータから`ym`パラメータを抽出（`?ym=YYYYMM`の形式で結合）
- `language`パラメータがあれば`&language=...`の形式で追加
- 重複を削除してソート

### diff_api_response.py

**機能:**
- `target_path`ファイルからAPIパスを読み込み
- 各パスに対してv1.0とv2.0のAPIにGETリクエストを送信
- HTTPステータスコードとレスポンスボディを比較
- 不一致があれば詳細を出力

**設定:**
- `base_url_v1`: v1.0のAPIベースURL（デフォルト: `https://stg-blog-internal-api.tama.local/v1.0`）
- `base_url_v2`: v2.0のAPIベースURL（デフォルト: `https://stg-blog-internal-api.tama.local/v2.0`）
- タイムアウト: 10秒（curlコマンド）、15秒（subprocess）

**比較ロジック:**
1. HTTPステータスコードを比較
   - 異なる場合は不一致として出力
2. レスポンスボディを比較
   - JSONを正規化（キーをソート）して比較
   - 一致しない場合は不一致として出力

**エラーハンドリング:**
- 接続エラー: エラーメッセージを表示して次のパスに進む
- タイムアウト: エラーメッセージを表示して次のパスに進む
- HTTPエラー（4xx, 5xx）: ステータスコードが同じ場合は一致として扱う

## 注意事項

- `diff_api_response.py`は`--insecure`オプションを使用してSSL証明書の検証を無効化しています（開発環境用）
- 本番環境で使用する場合は、SSL証明書の検証を有効にすることを推奨します
- 大量のパスを処理する場合、実行に時間がかかる可能性があります

